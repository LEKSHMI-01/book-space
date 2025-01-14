from flask import Flask, render_template, request, redirect, url_for, session
import datetime
import secrets
import csv


app = Flask(__name__)
secret_key = secrets.token_hex(16)
app.secret_key = secret_key


users = []

class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password

def find_user(username):
    for user in users:
        if user.username == username:
            return user
    return None


class ParkingSlot:
    def __init__(self, slot_id, available=True):
        self.slot_id = slot_id
        self.available = available
        self.booking_id = None
        self.booking_details = {}
        self.exit_time = None  # New exit_time attribute

    def extend_booking(self, exit_time):
        self.exit_time = exit_time

class ParkingLot:
    def __init__(self, num_slots):
        self.slots = [ParkingSlot(slot_id) for slot_id in range(1, num_slots + 1)]
        self.booking_details_file = 'booking_details.csv'

    def display_available_slots(self):
        return [slot.slot_id for slot in self.slots if slot.available]

    def book_slot(self, slot_id, booking_id, name, vehicle_number, date, entry_time, exit_time):
        slot = self.get_slot_by_id(slot_id)
        if slot:
            if slot.available:
                slot.available = False
                slot.booking_id = booking_id
                slot.booking_details = {
                    'Name': name,
                    'Vehicle Number': vehicle_number,
                    'Date': date,
                    'Entry Time': entry_time,
                    'Exit Time': exit_time
                }
                with open(self.booking_details_file, 'a', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([booking_id, slot_id, name, vehicle_number, date, entry_time, exit_time])

                return True
            else:
                return False
        else:
            return False

    def cancel_booking(self, booking_id):
        slot = self.get_slot_by_booking_id(booking_id)
        if slot:
            slot.available = True
            slot.booking_id = None
            slot.booking_details = {}
            slot.exit_time = None  # Reset exit_time to None

            with open(self.booking_details_file, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

            with open(self.booking_details_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for row in rows:
                    if row[0] != booking_id:
                        writer.writerow(row)

            return True
        else:
            return False

    def extend_booking(self, booking_id, exit_time):
        slot = self.get_slot_by_booking_id(booking_id)
        if slot:
            slot.extend_booking(exit_time)

            with open(self.booking_details_file, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

            with open(self.booking_details_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for row in rows:
                    if row[0] == booking_id:
                        row[6] = exit_time  # Update exit_time in the CSV row
                    writer.writerow(row)

            return True
        else:
            return False

    def get_slot_by_id(self, slot_id):
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        return None

    def get_slot_by_booking_id(self, booking_id):
        for slot in self.slots:
            if slot.booking_id == booking_id:
                return slot
        return None


def view_booked_slots():
    booking_details = []

    with open('booking_details.csv', 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            booking_id, slot_id, name, vehicle_number, date, entry_time, exit_time = row
            booking_details.append({
                'BookingID': booking_id,
                'Name': name,
                'VehicleNumber': vehicle_number,
                'Date': date,
                'EntryTime': entry_time,
                'ExitTime': exit_time
            })

    return booking_details

parking_lot = ParkingLot(10)

@app.route('/')
def index():
    session.clear()
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if find_user(username):
            return render_template('register.html', error_message="Username already exists")

        user = User(username, password)
        users.append(user)

        return redirect('/login')
    else:
        return render_template('register.html', error_message=None)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = find_user(username)
        if user and user.password == password:
            session['username'] = username  # Store the username in the session
            return redirect('/home')
        else:
            return render_template('login.html', error_message="Invalid username or password")

    return render_template('login.html', error_message=None)



@app.route('/home')
def home():
    if 'username' in session:  # Check if the user is logged in
        return render_template('index.html')
    else:
        return redirect('/')
    
@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    return redirect('/')



@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        slot_id = int(request.form['slot_id'])
        name = request.form['name']
        vehicle_number = request.form['vehicle_number']
        date = request.form['date']
        entry_time = request.form['entry_time']
        exit_time = request.form['exit_time']

        # Generate a booking ID
        booking_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        # Book a slot
        booking_successful = parking_lot.book_slot(slot_id, booking_id, name, vehicle_number, date, entry_time, exit_time)

        if booking_successful:
            return render_template('booked.html', slot_id=slot_id, booking_id=booking_id)
        else:
            return render_template('book.html', available_slots=parking_lot.display_available_slots(), error_message="Slot not available")
    else:
        return render_template('book.html', available_slots=parking_lot.display_available_slots(), error_message=None)

@app.route('/cancel', methods=['GET', 'POST'])
def cancel():
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        cancellation_successful = parking_lot.cancel_booking(booking_id)

        if cancellation_successful:
            return render_template('cancel.html', booking_id=booking_id, cancellation_message="Booking canceled successfully")
        else:
            return render_template('cancel.html', booking_id=None, cancellation_message=None, error_message="Invalid booking ID")
    else:
        return render_template('cancel.html', booking_id=None, cancellation_message=None, error_message=None)

@app.route('/extend', methods=['GET', 'POST'])
def extend():
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        exit_time = request.form['exit_time']

        extension_successful = parking_lot.extend_booking(booking_id, exit_time)

        if extension_successful:
            return render_template('extended.html', booking_id=booking_id)  # Redirect to success page
        else:
            return render_template('extend.html', error_message="Invalid booking ID")  # Show error message on the same page
    else:
        return render_template('extend.html', error_message=None)



@app.route('/slot', methods=['GET', 'POST'])
def slot():
    if request.method == 'POST':
        key = "admin@123"
        password = request.form['admin_pass']
        if password == key:
            booking_details = view_booked_slots()
            return render_template('slots.html', booking_details=booking_details)
        else:
            return render_template('error.html')
    return render_template('slotlist.html')

if __name__ == '__main__':
    name = '__main__'
    app.run(debug=True, port=8000)
