-- Drop existing tables to avoid conflicts
PROMPT DROP TABLES;

DROP TABLE HAS CASCADE CONSTRAINTS;
DROP TABLE BOOKING CASCADE CONSTRAINTS;
DROP TABLE CUSTOMERS CASCADE CONSTRAINTS;
DROP TABLE FLIGHTS CASCADE CONSTRAINTS;

-- Create Flights table
CREATE TABLE FLIGHTS (
    FLIGHT_NO	VARCHAR(5)  NOT NULL,
    SOURCE	VARCHAR(20) NOT NULL,
    DEST	VARCHAR(20) NOT NULL,
    DEPART_TIME DATE    NOT NULL,
    ARRIVE_TIME DATE    NOT NULL,
    FARE    INTEGER NOT NULL,
    SEAT_LIMIT  INTEGER NOT NULL,
    PRIMARY KEY (FLIGHT_NO)
    );

-- Insert sample data into Flights
PROMPT INSERT FLIGHTS TABLE;

INSERT INTO FLIGHTS VALUES('CX100', 'HK', 'Tokyo', to_date('15/3/2026,12:00:00', 'dd/mm/yyyy,hh24:mi:ss'), to_date('15/3/2026,16:00:00', 'dd/mm/yyyy,hh24:mi:ss'), 2000, 3);
INSERT INTO FLIGHTS VALUES('CX101', 'Tokyo', 'New York', to_date('15/3/2026,18:30:00', 'dd/mm/yyyy,hh24:mi:ss'), to_date('15/3/2026,23:30:00', 'dd/mm/yyyy,hh24:mi:ss'), 4000, 3);
INSERT INTO FLIGHTS VALUES('CX102', 'HK', 'Beijing', to_date('15/3/2026,10:00:00', 'dd/mm/yyyy,hh24:mi:ss'), to_date('15/3/2026,13:00:00', 'dd/mm/yyyy,hh24:mi:ss'), 2000, 1);
INSERT INTO FLIGHTS VALUES('CX103', 'Beijing', 'Tokyo', to_date('15/3/2026,15:00:00', 'dd/mm/yyyy,hh24:mi:ss'), to_date('15/3/2026,18:00:00', 'dd/mm/yyyy,hh24:mi:ss'), 1500, 3);
INSERT INTO FLIGHTS VALUES('CX104', 'New York', 'Beijing', to_date('15/3/2026,10:00:00', 'dd/mm/yyyy,hh24:mi:ss'), to_date('15/3/2026,14:00:00', 'dd/mm/yyyy,hh24:mi:ss'), 1500, 3);
INSERT INTO FLIGHTS VALUES('CX105', 'HK', 'New York', to_date('15/3/2026,04:00:00','dd/mm/yyyy,hh24:mi:ss'),  to_date('15/3/2026,09:00:00','dd/mm/yyyy,hh24:mi:ss'), 1000, 2);
INSERT INTO FLIGHTS VALUES('CX106', 'New York', 'LA', to_date('15/3/2026,23:40:00', 'dd/mm/yyyy,hh24:mi:ss'), to_date('16/3/2026,03:00:00', 'dd/mm/yyyy,hh24:mi:ss'), 5000, 3);
INSERT INTO FLIGHTS VALUES('CX107', 'Beijing', 'Tokyo', to_date('15/3/2026,08:00:00','dd/mm/yyyy,hh24:mi:ss'), to_date('15/3/2026,11:00:00','dd/mm/yyyy,hh24:mi:ss'), 1500, 3);

COMMIT;

-- Create Customers table
CREATE TABLE CUSTOMERS (
    CID CHAR(3) NOT NULL,
    CNAME   VARCHAR(20) NOT NULL,
    NATIONALITY VARCHAR(3)  NOT NULL,
    PASSPORT    VARCHAR(8)  NOT NULL,
    PRIMARY KEY (CID),
    UNIQUE (PASSPORT)
    );

-- Insert sample data into Customers
PROMPT INSERT CUSTOMERS TABLE;

INSERT INTO CUSTOMERS VALUES('C01', 'Alice', 'CHN', 'P1234567');
INSERT INTO CUSTOMERS VALUES('C02', 'Bob', 'UK', 'P1111111');
INSERT INTO CUSTOMERS VALUES('C03', 'Cole', 'US', 'P7654321');

COMMIT;

PROMPT INSERT BOOKING TABLE AND ITS RELATIONSHIP;

-- Create Booking table and Has relationship table
CREATE TABLE BOOKING (
    BID VARCHAR(5),
    CID CHAR(3) NOT NULL,
    BFARE   REAL    DEFAULT 0.00    NOT NULL,
    FCOUNT  INTEGER DEFAULT 0   NOT NULL,
    PRIMARY KEY (BID),
    FOREIGN KEY (CID) REFERENCES CUSTOMERS (CID)
    );

CREATE TABLE HAS (
    BID VARCHAR(5) NOT NULL,
    FLIGHT_NO VARCHAR(5) NOT NULL,
    FSEQUENCE INTEGER   NOT NULL,
    PRIMARY KEY (BID, FLIGHT_NO),
    FOREIGN KEY (BID) REFERENCES BOOKING (BID) ON DELETE CASCADE,
    FOREIGN KEY (FLIGHT_NO) REFERENCES FLIGHTS (FLIGHT_NO) ON DELETE CASCADE
    );

PROMPT INSERT CONSTRAINTS;

-- Create triggers for maintaining FCOUNT (The number of flights in a booking)
CREATE OR REPLACE TRIGGER ADD_FCOUNT
AFTER INSERT ON HAS
FOR EACH ROW
BEGIN
    UPDATE BOOKING SET FCOUNT = FCOUNT + 1 WHERE BID = :new.BID;
END;
/

-- Create trigger for maintaining FCOUNT <= 3
CREATE OR REPLACE TRIGGER FCOUNT_constraint
BEFORE INSERT ON HAS
FOR EACH ROW
DECLARE
    c   INTEGER;
BEGIN
    SELECT FCOUNT INTO c FROM BOOKING WHERE BID = :new.BID;
    IF (c >= 3) THEN
        RAISE_APPLICATION_ERROR(-20000, 'Reach max transfer times');
    END IF;
END;
/

-- Create trigger for generating squence number for each flight in a booking
CREATE OR REPLACE TRIGGER GEN_SEQUENCE
BEFORE INSERT ON HAS
FOR EACH ROW
DECLARE
    ec   INTEGER;
BEGIN
    SELECT FCOUNT INTO ec FROM BOOKING WHERE BID = :new.BID;
    :new.FSEQUENCE := ec + 1;
END;
/

-- Create trigger for verifying the connection (the destination of the previous flight should be the same as the source of the next flight, and the departure time of the next flight should be later than the arrival time of the previous flight)
CREATE OR REPLACE TRIGGER CONNECTION_VERIFICATION
BEFORE INSERT ON HAS
FOR EACH ROW
DECLARE
    cs  INTEGER;
    pdest   VARCHAR(20);
    ptime   DATE;
    csource VARCHAR(20);
    ctime   DATE;
BEGIN
    SELECT FCOUNT INTO cs FROM BOOKING WHERE BID = :new.BID;
    IF (cs > 0) THEN
        SELECT F.DEST, F.ARRIVE_TIME INTO pdest, ptime
        FROM FLIGHTS F INNER JOIN HAS H
        ON F.FLIGHT_NO = H.FLIGHT_NO
        WHERE H.BID = :new.BID AND H.FSEQUENCE = cs;

        SELECT SOURCE, DEPART_TIME INTO csource, ctime
        FROM FLIGHTS
        WHERE FLIGHT_NO = :new.FLIGHT_NO;
        IF (pdest <> csource OR ptime > ctime) THEN
            RAISE_APPLICATION_ERROR(-20001, 'Unable to connect with the previous flight');
        END IF;
    END IF;
END;
/

-- Create trigger for balancing SEAT_LIMIT in FLIGHTS table when booking is created or cancelled
CREATE OR REPLACE TRIGGER BOOKING_CREATE
AFTER INSERT ON HAS
FOR EACH ROW
DECLARE
    f   INTEGER;
BEGIN
    UPDATE FLIGHTS SET SEAT_LIMIT = SEAT_LIMIT - 1 WHERE FLIGHT_NO = :new.FLIGHT_NO;
END;
/

CREATE OR REPLACE TRIGGER BOOKING_CANCEL
AFTER DELETE ON HAS
FOR EACH ROW
BEGIN
    UPDATE FLIGHTS SET SEAT_LIMIT = SEAT_LIMIT + 1 WHERE FLIGHT_NO = :old.FLIGHT_NO;
END;
/

CREATE OR REPLACE TRIGGER SEAT_LIMIT_constraint
BEFORE INSERT ON HAS
FOR EACH ROW
DECLARE
    l   INTEGER;
BEGIN
    SELECT SEAT_LIMIT INTO l FROM FLIGHTS WHERE FLIGHT_NO = :new.FLIGHT_NO;
    IF (l < 1) THEN
        DELETE FROM BOOKING WHERE BID = :new.BID;
        RAISE_APPLICATION_ERROR(-20000, 'Flight ' || :new.FLIGHT_NO || ' is fully booked! Booking terminated.');
    END IF;
END;
/
PROMPT CONSTRAINT INSERTION COMPLETE