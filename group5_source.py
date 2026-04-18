import warnings
warnings.filterwarnings('ignore', 'TripleDES has been moved')

import pwinput
import re
from colorama import Fore, Style
from types import SimpleNamespace

import atexit

from sshtunnel import SSHTunnelForwarder, BaseSSHTunnelForwarderError
import oracledb

''' Global variables'''
tunnel:SSHTunnelForwarder = None
cursor:oracledb.Cursor = None
connection:oracledb.Connection = None

db_info = SimpleNamespace(
    gateway = "faith.comp.hkbu.edu.hk",
    gw_port = 22,
    ora_host = "orasrv1.comp.hkbu.edu.hk",
    ora_port = 1521,
    srv_name = "pdborcl"
)

def on_exit()->None:
    '''
    A callback function that will be called automatically when the program terminates. It closes all connections and release the resources.
    '''

    try:
        cursor.close()
    except:
        pass
    try:
        connection.close()
    except:
        pass
    try:
        tunnel.stop()
    except:
        pass
    print("\n\nAll connections are closed. Good bye!\n\n")


def login_ssh_tunnel()->None:
    '''
    Creates a SSH tunnel.
    '''

    use = input("\nDo you want to use SSH Tunnel? (Y/N) ").strip()
    if len(use) == 0 or (use[0] not in "Yy"):
        return 
    
    username = input("\nEnter your COMP username: ").strip()
    password = pwinput.pwinput(prompt=f"Enter password for {username}/COMP: ", mask="·").strip()

    # you can hardcode your username and password here for testing, but make sure to remove them before submission
    # username = "" 
    # password = ""

    global tunnel

    try:
        tunnel = SSHTunnelForwarder(
            (db_info.gateway, db_info.gw_port),
            ssh_username = username, 
            ssh_password =password, 
            remote_bind_address = (db_info.ora_host, db_info.ora_port),
            local_bind_address = ("localhost", 0))

        tunnel.start()
        db_info.ora_host = "localhost"
        db_info.ora_port = tunnel.local_bind_port
        print(Fore.LIGHTCYAN_EX + f"Tunnel established at localhost:{tunnel.local_bind_port}\n" + Style.RESET_ALL)

    except (ValueError, BaseSSHTunnelForwarderError) as ex:
        # print(ex)
        print(Fore.RED + "Could not enable the SSH tunnel." + Style.RESET_ALL)
        exit()


def login_db()->None:
    '''
    Logs into the Oracle database
    '''

    username = input("\nEnter your Oracle username: ").strip()
    password = pwinput.pwinput(prompt=f"Enter password for {username}@jumbo: ", mask="·").strip()

    # you can hardcode your username and password here for testing, but make sure to remove them before submission
    # username = "" 
    # password = ""


    global connection, cursor

    dsn = f"{db_info.ora_host}:{db_info.ora_port}/{db_info.srv_name}"

    try:
        connection = oracledb.connect(user = username, password = password, dsn=dsn)
        cursor = connection.cursor()
        
        cursor.execute("SELECT banner FROM v$version")

        print(Fore.LIGHTCYAN_EX + f"\nConnected to {cursor.fetchone()[0]}\n" + Style.RESET_ALL)

    except oracledb.DatabaseError as ex:
        # print(ex) # release this line to see the raw error message for debugging
        print(Fore.RED + "Invalid username or password. Login denied." + Style.RESET_ALL)
        exit()


def list_flights()->None:
    '''
    Prints all flight numbers.
    '''

    cursor.execute("SELECT flight_no FROM flights ORDER BY flight_no ASC")
    rows = cursor.fetchall()

    print(Fore.GREEN)

    for row in rows:
        print(row[0])

    print(Style.RESET_ALL)

def print_flight(flight_no:str)->None:
    '''
    Prints the info of the specific flight.
    '''

    columns = ["Flight_no", "Departure Time", "Arrive Time", "Fare", "Seat Limit", "Source", "Dest"]


    cursor.execute("SELECT flight_no, depart_time, arrive_time, fare, seat_limit, source, dest FROM flights WHERE flight_no = :1", [flight_no])
    row = cursor.fetchone()

    if row is None:
        print(f"Flight {flight_no} not found.")
    else:
        print(Fore.YELLOW)

        for i in range(len(columns)):
            print(f"{columns[i] :>15}: {row[i]}")

        print(Style.RESET_ALL)

def flight_info()->None:
    '''
    Prompts user input for a flight number and prints the info of the specific flight.
    '''

    list_flights()
    print("-" * 40)
    flight_no = input("Enter a flight no. for the flight info: ").strip()
    print()

    if len(flight_no) > 0:
        print_flight(flight_no)
        print("=" * 40)

def add_flight()->None:
    '''
    Adds a new flight to the database. The user is prompted to input all the necessary info of the flight, separated by commas.
    '''

    data = input("Enter the flight info (Flight No., Departure Time, Arrive Time, Fare, Seat Limit, From, To): ").strip()
    data = [t.strip() for t in data.split(',') if t]

    if len(data) < 7:
        print(Fore.RED + "Invalid input." + Style.RESET_ALL)
        return

    try:
        cursor.execute("INSERT INTO flights (flight_no, depart_time, arrive_time, fare, seat_limit, source, dest) VALUES (:1, TO_DATE(:2, 'YYYY-MM-DD HH24:MI:SS'), TO_DATE(:3, 'YYYY-MM-DD HH24:MI:SS'),:4, :5, :6, :7)", data)
        connection.commit()

        print(f"Succeed to add flight {data[0]}.")
    except Exception as ex:
        # print(ex) # release this line to see the raw error message for debugging
        print(Fore.RED + "Fail to create a new flight." + Style.RESET_ALL)
        print(cursor.warning)

def del_flight()->None:
    '''
    Deletes a flight from the database. The user is prompted to input the flight number of the flight to be deleted.
    '''

    list_flights()
    print("-" * 40)    
    flight_no = input("Enter the number of the flight you want to delete: ").strip()

    if len(flight_no) == 0:
        print(Fore.RED + "Invalid input." + Style.RESET_ALL)
        return
    
    ...

    try:
        cursor.execute("DELETE FROM flights WHERE flight_no = :1", [flight_no])
        connection.commit()

        print(f"The flight {flight_no} has been deleted.")
    
    except Exception as ex:
        # print(ex) # release this line to see the raw error message for debugging
        print(f"Fail to delete flight {flight_no}")

def calculate_fare(flight_list)->float:
    fares = []
    for fn in flight_list:
        cursor.execute("SELECT fare FROM flights WHERE flight_no = :1", [fn])
        row = cursor.fetchone()
        fares.append(float(row[0]))

    s = sum(fares)
    n = len(fares)

    if n == 1:
        return round(s, 2)
    elif n == 2:
        return round(s * 0.90, 2)
    elif n == 3:
        return round(s * 0.75, 2)
    return 0


def zero_stop_flights(source: str, dest: str, max_time:int)->None:
    cursor.execute("SELECT COUNT(*) FROM FLIGHTS WHERE source = :1 AND dest = :2 AND ARRIVE_TIME - DEPART_TIME <= :3", (source, dest, max_time))
    total = cursor.fetchone()[0]
    print(f"\nTotal {total} choice(s)")
    cursor.execute(
        "SELECT flight_no FROM FLIGHTS WHERE source = :1 AND dest = :2 AND (ARRIVE_TIME-DEPART_TIME)*24<=:3 ORDER BY depart_time ASC",
        (source, dest, max_time)
    )
    rows = cursor.fetchall()

    for idx, row in enumerate(rows, start=1):
        flight_no = row[0]
        fare = calculate_fare([flight_no])
        print(f"({idx}) {flight_no}, fare: {int(fare) if fare.is_integer() else fare}")



def one_stop_flights(source: str, dest: str, max_time:int)->None:
    cursor.execute("SELECT A.flight_no, B.flight_no FROM flights A JOIN flights B ON A.dest = B.source WHERE A.arrive_time < B.depart_time AND A.source = :1 AND B.dest = :2 AND (B.ARRIVE_TIME-A.DEPART_TIME)*24<=:3 ORDER BY A.depart_time ASC",(source, dest,max_time))
    rows = cursor.fetchall()

    print(f"\nTotal {len(rows)} choice(s)")
    print(f"\nOne-stop flight from {source} to {dest}")
    print("=" *40)

    for idx, row in enumerate(rows, start=1):
        flight1 = row[0]
        flight2 = row[1]
        fare = calculate_fare([flight1, flight2])  
        print(f"({idx}) {flight1}->{flight2}, fare: {int(fare) if fare.is_integer() else fare}")



def two_stop_flights(source: str, dest: str, max_time:int)->None:
    cursor.execute("SELECT A.flight_no, B.flight_no, C.flight_no FROM flights A JOIN flights B ON A.dest = B.source JOIN flights C on B.dest=C.source WHERE A.arrive_time < B.depart_time AND B.arrive_time < C.depart_time AND A.source = :1 AND C.dest = :2 AND (C.ARRIVE_TIME-A.DEPART_TIME)*24<=:3 ORDER BY A.depart_time ASC",(source, dest,max_time))
    rows = cursor.fetchall()

    print(f"\nTotal {len(rows)} choice(s)")
    print(f"\nTwo-stop flight from {source} to {dest}")
    print("=" *40)

    for idx, row in enumerate(rows, start=1):
        flight1 = row[0]
        flight2 = row[1]
        flight3 = row[2]
        fare = calculate_fare([flight1, flight2, flight3])
        print(f"({idx}) {flight1}->{flight2}->{flight3}, fare: {int(fare) if fare.is_integer() else fare}")

def search_flight()->None:
    data = input("Enter the source, destination, stop times and maximum time: ")
    data = [t.strip() for t in data.split(',') if t]

    if len(data) < 4:
        print(Fore.RED + "Invalid input." + Style.RESET_ALL)
        return 

    source = data[0]
    destination = data[1]
    stop_times = data[2]
    max_time = int(data[3])

    try:
        stop_num = int(stop_times)
        if stop_num > 2:
            print(Fore.RED + "Please enter a number within 3." + Style.RESET_ALL)
            return
    except:
        print(Fore.RED + "Invalid input." + Style.RESET_ALL)
        return

    all_flights = []
    if int(stop_times) >= 0:
        cursor.execute(
            "SELECT flight_no FROM FLIGHTS WHERE source = :1 AND dest = :2 AND (ARRIVE_TIME - DEPART_TIME)*24 <= :3 ORDER BY depart_time ASC",
            (source, destination, max_time)
        )
        for row in cursor.fetchall():
            all_flights.append( [row[0]] )

    if int(stop_times) >= 1:
        cursor.execute(
            "SELECT A.flight_no, B.flight_no FROM flights A JOIN flights B ON A.dest = B.source WHERE A.arrive_time < B.depart_time AND A.source = :1 AND B.dest = :2 AND (B.ARRIVE_TIME-A.DEPART_TIME)*24<=:3 ORDER BY A.depart_time ASC",
            (source, destination, max_time)
        )
        for row in cursor.fetchall():
           all_flights.append( list(row) )

    if int(stop_times) >= 2:
        cursor.execute(
            "SELECT A.flight_no, B.flight_no, C.flight_no FROM flights A JOIN flights B ON A.dest = B.source JOIN flights C on B.dest=C.source WHERE A.arrive_time < B.depart_time AND B.arrive_time < C.depart_time AND A.source = :1 AND C.dest = :2 AND (C.ARRIVE_TIME-A.DEPART_TIME)*24<=:3 ORDER BY A.depart_time ASC",
            (source, destination, max_time)
        )
        for row in cursor.fetchall():
            all_flights.append( list(row) )

    print(f"\nTotal {len(all_flights)} choice(s):")
    print("=" * 40)
    for idx, flight_list in enumerate(all_flights, start=1):
        flight_str = "->".join(flight_list)
        fare = calculate_fare(flight_list)
        print(f"({idx}) {flight_str}, fare: {int(fare) if fare.is_integer() else fare}")

        #print(rows) # release this line to see the raw query result for debugging


def make_booking()->None:
    print("Book a flight by inputting customer id and flight no")
    print("Format: Customer_ID, Flight_NO, Flight_NO, Flight_NO (if any)")
    print("Example: C01, CX105, CX104")
    data_input = input("Enter: ")
    data = [t.strip() for t in data_input.split(',') if t.strip()]
    if len(data) <= 1:
        print(Fore.RED + "Invalid input. Please try again" + Style.RESET_ALL)
        return
    else:
        cust_data, *flight_data = data

    sql = "SELECT * FROM CUSTOMERS WHERE CID = :1"
    cursor.execute(sql, [cust_data])
    cust_return = cursor.fetchone()
    if not cust_return:
        print(Fore.RED + f"Customer {cust_data} does not exist! Please try again" + Style.RESET_ALL)
        return
    
    sql = "SELECT * FROM FLIGHTS WHERE FLIGHT_NO = :1"
    for flight in flight_data:
        cursor.execute(sql, [flight])
        flight_return = cursor.fetchone()
        if not flight_return:
            print(Fore.RED + f"Flight {flight} not exist!" + Style.RESET_ALL)
            return

    cursor.execute("SELECT MAX(TO_NUMBER(SUBSTR(BID, 2))) FROM BOOKING")
    max_bid = cursor.fetchone()[0]
    if not max_bid:
        current_bid = "B1"
    else:
        current_bid = f"B{max_bid + 1:d}"
    current_booking_fare = calculate_fare(flight_data)

    try:
        # Insert value into BOOKING
        sql = "INSERT INTO BOOKING(BID, CID, BFARE) VALUES(:1, :2, :3)"
        booking_info = [current_bid, cust_data, current_booking_fare]
        cursor.execute(sql, booking_info)

        # Insert value into HAS
        for flight in flight_data:
            has_info = [current_bid, flight]
            sql = "INSERT INTO HAS(BID, FLIGHT_NO) VALUES(:1, :2)"
            cursor.execute(sql, has_info)
        connection.commit()

        print(Fore.GREEN + "Booking successful" + Style.RESET_ALL)
    except oracledb.DatabaseError as ex:
        connection.rollback()

        error_obj = ex.args[0]
        err_code = error_obj.code
        err_msg = error_obj.message
        
        if err_code == 20000 or err_code == 20001 or err_code == 20002:
            print(Fore.RED + f"{err_msg.splitlines()[0].split(': ', 1)[-1]}" + Style.RESET_ALL)
        else:
            print(Fore.RED + "Invaild input." + Style.RESET_ALL)
        
        print(Fore.RED + "Failed to place this booking." + Style.RESET_ALL)
    except Exception as ex:
        # print(ex) # release this line to see the raw error message for debugging
        print(Fore.RED + "Failed to place this booking." + Style.RESET_ALL)
        print(cursor.warning)


def cancel_booking()->None:
   
    print("\n" + "=" * 50)
    print("CANCEL BOOKING")
    print("=" * 50)
    print("Format: Customer_ID, Booking_ID")
    print("Example: C01, B1")
    
    data = input("Enter: ").strip()
    data = [t.strip() for t in data.split(',') if t]
    
    if len(data) < 2:
        print(Fore.RED + "Invalid input. Need Customer_ID and Booking_ID." + Style.RESET_ALL)
        return
    
    customer_id = data[0].upper()
    booking_id = data[1].upper()
    
    
    cursor.execute("SELECT CID FROM BOOKING WHERE CID = :1", [customer_id])
    customer = cursor.fetchone()
    if not customer:
        print(Fore.RED + f"Customer {customer_id} not found in booking!" + Style.RESET_ALL)
        return
    
   
    cursor.execute("SELECT BID FROM BOOKING WHERE BID = :1 AND CID = :2",[booking_id, customer_id])
    
    booking_exists = cursor.fetchone()
    if not booking_exists:
        print(Fore.RED + f"Booking {booking_id} not found for customer {customer_id}!" + Style.RESET_ALL)
        return
    
   
    cursor.execute("SELECT COUNT(*) FROM HAS WHERE BID = :1", [booking_id])
    has_count = cursor.fetchone()[0]
    if has_count == 0:
        print(Fore.RED + f"Booking {booking_id} customer {customer_id} fails to cancel!" + Style.RESET_ALL)
        return
    
  
    cursor.execute("SELECT FLIGHT_NO FROM HAS WHERE BID = :1", [booking_id])
    flights = cursor.fetchall()
    flight_list = [f[0] for f in flights]
    
    try:
        
        cursor.execute("DELETE FROM HAS WHERE BID = :1", [booking_id])
        connection.commit()
        
      
        print(Fore.GREEN + f"\n✓ Booking {booking_id} for customer {customer_id} is cancelled!" + Style.RESET_ALL)
        print(f"  Cancelled flights: {' -> '.join(flight_list)}")
        
        
    except Exception as e:
        connection.rollback()
        print(Fore.RED + f"✗ Cancellation failed: {str(e)}" + Style.RESET_ALL)

def print_menu()->None:
    print(Fore.CYAN)
    print("(1) Add flight")
    print("(2) Display flight info")
    print("(3) Delete flight")
    print("(4) Search Flight")
    print("(5) Make your booking")
    print("(6) Cancel booking")
    print("(7) Quit")
    print(Style.RESET_ALL)
    print("-" * 40)

atexit.register(on_exit)

login_ssh_tunnel()
login_db()

print("Welcome to use Flight Manager\n")

while True:
    print_menu()
    option = input("Please choose an option (1 - 7): ").strip()

    if option == "1":
        add_flight()
    elif option == "2":
        flight_info()
    elif option == "3":
        del_flight()
    elif option == "4":
        search_flight()
    elif option == "5":
        make_booking()
    elif option == "6":
        cancel_booking()
    elif option == "7":
        break
    else:
        print("Invalid option number.")
