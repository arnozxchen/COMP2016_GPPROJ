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

    columns = ["Flight No.", "From", "To", "Departure Time", "Arrive Time", "Fare"]


    cursor.execute("SELECT flight_no, source, dest, depart_time, arrive_time, fare FROM flights WHERE flight_no = :1", [flight_no])
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

    data = input("Enter the flight info (Flight No., From, To, Departure Time, Arrive Time, Fare): ").strip()
    data = [t.strip() for t in data.split(',') if t]

    if len(data) < 6:
        print(Fore.RED + "Invalid input." + Style.RESET_ALL)
        return

    try:
        cursor.execute("INSERT INTO flights (flight_no, source, dest, depart_time, arrive_time, fare) VALUES (:1, :2, :3, TO_DATE(:4, 'YYYY-MM-DD HH24:MI:SS'), TO_DATE(:5, 'YYYY-MM-DD HH24:MI:SS'), :6)", data)
        connection.commit()

        print(f"Created Flight {data[0]} successfully.")
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



def zero_stop_flights(source: str, dest: str, max_time:int)->None:
    cursor.execute("SELECT COUNT(*) FROM FLIGHTS WHERE source = :1 AND dest = :2 AND ARRIVE_TIME - DEPART_TIME <= :3", (source, destination, max_time))
    total = cursor.fetchone()[0]
    print(f"\nTotal {total} choice(s)")
    cursor.execute("SELECT flight_no FROM FLIGHTS WHERE source = :1 AND dest = :2 AND ARRIVE_TIME-DEPART_TIME<=:3 ORDER BY depart_time ASC", (source, dest,max_time) )
    rows = cursor.fetchall()

    print(f"\nZero-stop flight from {source} to {dest}")
    print("=" * 40)

    print(row[0])
    print



def one_stop_flights(source: str, dest: str, max_time:int)->None:
    cursor.execute("SELECT A.flight_no, B.flight_no FROM flights A JOIN flights B ON A.dest = B.source WHERE A.arrive_time < B.depart_time AND A.source = :1 AND B.dest = :2 AND B.ARRIVE_TIME-A.DEPART_TIME<=:3 ORDER BY A.depart_time ASC",(source, dest,max_time))
    rows = cursor.fetchall()

    print(f"\nOne-stop flight from {source} to {dest}")
    print("=" *40)

    count = 0
    for row in rows:
        count += 1
        print_flight(row[0])
        print("-" * 40)
        print_flight(row[1])
        print("=" * 40)
    
    print(f"Found {count} flight{"s" if count != 1 else ""}")   



def two_stop_flights(source: str, dest: str, max_time:int)->None:
    cursor.execute("SELECT A.flight_no, B.flight_no, C.flight_no FROM flights A JOIN flights B ON A.dest = B.source JOIN flights C on B.dest=C.source WHERE A.arrive_time < B.depart_time AND B.arrive_time < C.depart_time AND A.source = :1 AND C.dest = :2 AND C.ARRIVE_TIME-A.DEPART_TIME<=:3 ORDER BY A.depart_time ASC",(source, dest,max_time))
    rows = cursor.fetchall()

    print(f"\nOne-stop flight from {source} to {dest}")
    print("=" *40)

    count = 0
    for row in rows:
        count += 1
        print_flight(row[0])
        print("-" * 40)
        print_flight(row[1])
        print("=" * 40)
    
    print(f"Found {count} flight{"s" if count != 1 else ""}")  

def search_flight()->None:
    data = input("Enter the source, destination, stop times and maximum time: ")
    data = [t.strip() for t in data.split(',') if t]

    if len(data) < 4:
        print(Fore.RED + "Invalid input." + Style.RESET_ALL)
        return 

    source = data[0]
    destination = data[1]
    stop_times = data[2]
    max_time = data[3]

    if stop_times == "1": 
        zero_stop_flights(source, destination, max_time)
    elif stop_times == "2":
        zero_stop_flights(source, destination, max_time)
        one_stop_flights(source, destination, max_time)
    elif stop_times == "3":
        zero_stop_flights(source, destination, max_time)
        one_stop_flights(source, destination, max_time)
        two_stop_flights(source, destination, max_time)

    # print(rows) # release this line to see the raw query result for debugging

    print(f"\nOne-stop flight from {data[0]} to {data[1]}")
    print("=" *40)

    count = 0
    for row in rows:
        count += 1
        print_flight(row[0])
        print("-" * 40)
        print_flight(row[1])
        print("=" * 40)
    
    print(f"Found {count} flight{"s" if count != 1 else ""}")   




def print_menu()->None:
    print(Fore.CYAN)
    print("(1) Add flight")
    print("(2) Display flight info")
    print("(3) Delete flight")
    print("(4) Search Flight")
    print("(5) ")
    print("(6) Quit")
    print(Style.RESET_ALL)
    print("-" * 40)

atexit.register(on_exit)

login_ssh_tunnel()
login_db()

print("Welcome to use Flight Manager\n")

while True:
    print_menu()
    option = input("Please choose an option (1 - 6): ").strip()

    if option == "1":
        add_flight()
    elif option == "2":
        flight_info()
    elif option == "3":
        del_flight()
    elif option == "4":
        search_flight()
    elif option == "5":
        
    # elif option == "6":
        break
    else:
        print("Invalid option number.")