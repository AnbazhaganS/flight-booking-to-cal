from flask import Flask, request, send_file, render_template
from datetime import datetime, timedelta
import re

app = Flask(__name__, template_folder='source/templates')

@app.route('/', methods=['GET'])
def index():
    # Ensure this path correctly points to your HTML file
    return render_template('index.html')
# ============================================================================

# PARSING THE USER-INPUT

# ============================================================================
def try_parse_time(time_str):
    for fmt in ("%I:%M %p", "%H:%M"):  # 12-hour format with AM/PM, then 24-hour format
        try:
            return datetime.strptime(time_str.strip(), fmt).time()
        except ValueError:
            continue
    return None  # or raise an exception if you prefer

def try_parse_date(date_str):
    for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None  # or raise an exception if you prefer

def find_with_keywords(text, keywords, default=None):
    for keyword in keywords:
        pattern = r"{} -? ([\d:APMapm]+)".format(keyword)
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return default

def parse_flight_details(details):
    # Example keywords; you can expand or modify this list
    departure_keywords = ["departure time", "hora de salida"]
    arrival_keywords = ["arrival time", "hora de llegada"]

    departure_time_str = find_with_keywords(details, departure_keywords)
    arrival_time_str = find_with_keywords(details, arrival_keywords)

    # Assuming date is always in a specific format; you may need to adjust this
    date_str = re.search(r"(\d{2}/\d{2}/\d{4})", details).group(1)

    # More generic parsing for flight code and destination
    flight_code_match = re.search(r"([A-Z]{2}\d+)", details)
    flight_code = flight_code_match.group(1) if flight_code_match else "Unknown Flight"

    destination_match = re.search(r"To (.+?) [A-Z]{2}\d+", details)
    destination = destination_match.group(1) if destination_match else "Unknown Destination"

    # Parse date and times
    date = try_parse_date(date_str)
    departure_time = try_parse_time(departure_time_str)
    arrival_time = try_parse_time(arrival_time_str)

    if not all([date, departure_time, arrival_time]):
        return None, None, None, None, None  # Invalid data

    return date, departure_time, arrival_time, destination, flight_code

# ============================================================================

# PARSING THE USER-INPUT

# ============================================================================

@app.route('/create-event', methods=['POST'])
def create_event():
    print("Received data:", request.form)  # Debug print
    booking_details = request.form['bookingDetails']
    date, departure_time, arrival_time, destination, flight_code = parse_flight_details(booking_details)

    if not date:
        return "Invalid booking details", 400

    start_datetime = datetime.combine(date, departure_time)
    end_datetime = datetime.combine(date, arrival_time)
    reminder_datetime = start_datetime - timedelta(hours=2)
    busy_start = start_datetime - timedelta(minutes=30)
    busy_end = end_datetime + timedelta(minutes=30)

    event_content = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        f"SUMMARY:Flight to {destination} ({flight_code})\n"
        f"DTSTART:{start_datetime.strftime('%Y%m%dT%H%M%S')}\n"
        f"DTEND:{end_datetime.strftime('%Y%m%dT%H%M%S')}\n"
        f"BEGIN:VALARM\n"
        f"TRIGGER:-PT120M\n"
        f"DESCRIPTION:Reminder to leave for your flight\n"
        f"END:VALARM\n"
        f"FREEBUSY;FBTYPE=BUSY:{busy_start.strftime('%Y%m%dT%H%M%S')}/{busy_end.strftime('%Y%m%dT%H%M%S')}\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )
    ics_filename = f"Your flight to {destination} on {date.strftime('%d-%m-%Y')}.ics"
    with open(ics_filename, "w") as file:
        file.write(event_content)

    return send_file(ics_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)