from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ticket_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'secret_key'

db = SQLAlchemy(app)


# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    is_blocked = db.Column(db.Boolean, default=False)
    projects = db.relationship('Project', backref='staff', lazy=True)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Draft')
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attachments = db.relationship('TicketFile', backref='ticket', lazy=True)


class TicketFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)


# Routes
# Route for staff user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'Invalid email or password.'}), 401

    if user.is_blocked:
        return jsonify({'message': 'Your account has been blocked.'}), 403

    if password != user.password:
        return jsonify({'message': 'Invalid email or password.'}), 401

    session['user_id'] = user.id
    session['user_type'] = user.user_type

    return jsonify({'message': 'Login successful.'}), 200


# Route for staff user dashboard
@app.route('/staff/dashboard', methods=['GET'])
def staff_dashboard():
    if 'user_id' not in session or session['user_type'] != 'staff':
        print("session",session)
        return jsonify({'message': 'Unauthorized.'}), 401

    user_id = session['user_id']

    draft_tickets_count = Ticket.query.filter_by(staff_id=user_id, status='Draft').count()
    ongoing_tickets_count = Ticket.query.filter_by(staff_id=user_id, status='Ongoing').count()
    completed_tickets_count = Ticket.query.filter_by(staff_id=user_id, status='Completed').count()

    return jsonify({
        'draft_tickets_count': draft_tickets_count,
        'ongoing_tickets_count': ongoing_tickets_count,
        'completed_tickets_count': completed_tickets_count
    }), 200


# Route for staff user ticket list
@app.route('/staff/tickets', methods=['GET'])
def staff_tickets():
    if 'user_id' not in session or session['user_type'] != 'staff':
        return jsonify({'message': 'Unauthorized.'}), 401

    user_id = session['user_id']
    status = request.args.get('status')

    tickets_query = Ticket.query.filter_by(staff_id=user_id)

    if status:
        valid_statuses = ['Draft', 'Ongoing', 'Completed']
        if status not in valid_statuses:
            return jsonify({'message': 'Invalid status.'}), 400
        tickets_query = tickets_query.filter_by(status=status)

    tickets = tickets_query.all()

    tickets_data = []
    for ticket in tickets:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'description': ticket.description,
            'status': ticket.status,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at
        }
        tickets_data.append(ticket_data)

    return jsonify(tickets_data), 200


# Route for staff user updating ticket status
@app.route('/staff/tickets/<int:ticket_id>/status', methods=['PUT'])
def staff_update_ticket_status(ticket_id):
    if 'user_id' not in session or session['user_type'] != 'staff':
        return jsonify({'message': 'Unauthorized.'}), 401

    data = request.get_json()
    status = data.get('status')

    if not status:
        return jsonify({'message': 'Status is required.'}), 400

    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        return jsonify({'message': 'Ticket not found.'}), 404

    if ticket.staff_id != session['user_id']:
        return jsonify({'message': 'You are not authorized to update this ticket.'}), 403

    valid_statuses = ['Ongoing', 'Completed']
    if status not in valid_statuses:
        return jsonify({'message': 'Invalid status.'}), 400

    ticket.status = status
    db.session.commit()

    return jsonify({'message': 'Ticket status updated successfully.'}), 200


# Route for staff user logging out
@app.route('/staff/logout', methods=['POST'])
def staff_logout():
    if 'user_id' not in session or session['user_type'] != 'staff':
        return jsonify({'message': 'Unauthorized.'}), 401

    session.pop('user_id', None)
    session.pop('user_type', None)

    return jsonify({'message': 'Logged out successfully.'}), 200

# Create a staff user
@app.route('/admin/staff-users', methods=['POST'])
def create_staff_user():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')  # Add password field in the JSON request


    # Validate input
    if not email or not name or not password:
        return jsonify({'error': 'Email, name, and password are required.'}), 400

    # Validate password strength (example: minimum 8 characters with at least one uppercase and one digit)
    if len(password) < 8 or not any(char.isupper() for char in password) or not any(char.isdigit() for char in password):
        return jsonify({'error': 'Password should be at least 8 characters long and contain at least one uppercase letter and one digit.'}), 400

    # Create staff user
    staff_user = User(email=email, name=name, password=password,user_type="staff")  # Assuming User model has a 'password' field
    # Set additional staff user details

    db.session.add(staff_user)
    db.session.commit()
    return jsonify({'message': 'Staff user created successfully.'}), 201


# Edit details of an existing staff user
@app.route('/admin/staff-users/<staff_user_id>', methods=['PUT'])
def edit_staff_user(staff_user_id):
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    # Additional staff user details

    # Find staff user by ID
    staff_user = User.query.get(staff_user_id)
    if not staff_user:
        return jsonify({'error': 'Staff user not found.'}), 404

    # Update staff user details
    staff_user.email = email or staff_user.email
    staff_user.name = name or staff_user.name
    # Update additional staff user details

    db.session.commit()
    return jsonify({'message': 'Staff user updated successfully.'}), 200

# Block/unblock a staff user
@app.route('/admin/staff-users/<staff_user_id>/block', methods=['PUT'])
def block_staff_user(staff_user_id):
    # Find staff user by ID
    staff_user = User.query.get(staff_user_id)
    if not staff_user:
        return jsonify({'error': 'Staff user not found.'}), 404

    staff_user.blocked = True
    db.session.commit()
    return jsonify({'message': 'Staff user blocked successfully.'}), 200

@app.route('/admin/staff-users/<staff_user_id>/unblock', methods=['PUT'])
def unblock_staff_user(staff_user_id):
    # Find staff user by ID
    staff_user = User.query.get(staff_user_id)
    if not staff_user:
        return jsonify({'error': 'Staff user not found.'}), 404

    staff_user.blocked = False
    db.session.commit()
    return jsonify({'message': 'Staff user unblocked successfully.'}), 200

# Delete a staff user
@app.route('/admin/staff-users/<staff_user_id>', methods=['DELETE'])
def delete_staff_user(staff_user_id):
    # Find staff user by ID
    staff_user = User.query.get(staff_user_id)
    if not staff_user:
        return jsonify({'error': 'Staff user not found.'}), 404

    db.session.delete(staff_user)
    db.session.commit()
    return jsonify({'message': 'Staff user deleted successfully.'}), 200

# Route for creating a new ticket
@app.route('/tickets', methods=['POST'])
def create_ticket():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'message': 'Unauthorized.'}), 401

    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    assigned_staff_id = data.get('assigned_staff_id')

    if not name or not assigned_staff_id:
        return jsonify({'message': 'Name and assigned staff ID are required.'}), 400

    staff_user = User.query.get(assigned_staff_id)

    if not staff_user or staff_user.user_type != 'staff':
        return jsonify({'message': 'Invalid assigned staff ID.'}), 400

    ticket = Ticket(name=name, description=description, staff_id=assigned_staff_id)
    db.session.add(ticket)
    db.session.commit()

    return jsonify({'message': 'Ticket created successfully.'}), 201


# Route for editing a ticket
@app.route('/tickets/<int:ticket_id>', methods=['PUT'])
def edit_ticket(ticket_id):
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'message': 'Unauthorized.'}), 401

    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    assigned_staff_id = data.get('assigned_staff_id')

    if not name or not assigned_staff_id:
        return jsonify({'message': 'Name and assigned staff ID are required.'}), 400

    staff_user = User.query.get(assigned_staff_id)

    if not staff_user or staff_user.user_type != 'staff':
        return jsonify({'message': 'Invalid assigned staff ID.'}), 400

    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        return jsonify({'message': 'Ticket not found.'}), 404

    ticket.name = name
    ticket.description = description
    ticket.staff_id = assigned_staff_id
    db.session.commit()

    return jsonify({'message': 'Ticket updated successfully.'}), 200


# Route for changing ticket status
@app.route('/tickets/<int:ticket_id>/status', methods=['PUT'])
def change_ticket_status(ticket_id):
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'message': 'Unauthorized.'}), 401

    data = request.get_json()
    status = data.get('status')

    if not status:
        return jsonify({'message': 'Status is required.'}), 400

    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        return jsonify({'message': 'Ticket not found.'}), 404

    valid_statuses = ['Draft', 'Ongoing', 'Completed']

    if ticket.status == 'Completed' and status == 'Draft':
        return jsonify({'message': 'Archived tickets cannot be set to Draft status.'}), 400

    if status not in valid_statuses:
        return jsonify({'message': 'Invalid status.'}), 400

    ticket.status = status
    db.session.commit()

    return jsonify({'message': 'Ticket status updated successfully.'}), 200


# Route for archiving completed tickets
@app.route('/tickets/archive', methods=['PUT'])
def archive_tickets():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'message': 'Unauthorized.'}), 401

    tickets = Ticket.query.filter_by(status='Completed').all()

    for ticket in tickets:
        ticket.status = 'Archived'

    db.session.commit()

    return jsonify({'message': 'Tickets archived successfully.'}), 200


# Route for uploading ticket attachments
@app.route('/tickets/<int:ticket_id>/attachments', methods=['POST'])
def upload_attachment(ticket_id):
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'message': 'Unauthorized.'}), 401

    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        return jsonify({'message': 'Ticket not found.'}), 404

    if 'file' not in request.files:
        return jsonify({'message': 'No file provided.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'message': 'No file selected.'}), 400

    if file:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(os.getcwd(), 'media')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        ticket_file = TicketFile(filename=filename, ticket_id=ticket_id)
        db.session.add(ticket_file)
        db.session.commit()

        return jsonify({'message': 'Attachment uploaded successfully.'}), 201


# Route for viewing all users (admin only)
@app.route('/admin/users', methods=['GET'])
def view_all_users():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'message': 'Unauthorized.'}), 401

    users = User.query.all()

    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'user_type': user.user_type
        }
        users_data.append(user_data)

    return jsonify(users_data), 200


@app.route('/admin/tickets', methods=['GET'])
def view_all_tickets():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'message': 'Unauthorized.'}), 401

    tickets = Ticket.query.all()

    tickets_data = []
    for ticket in tickets:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'description': ticket.description,
            'status': ticket.status,
            'staff_id': ticket.staff_id,
            'attachments': []
        }

        # Get the file paths of ticket attachments
        attachments = TicketFile.query.filter_by(ticket_id=ticket.id).all()
        for attachment in attachments:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)
            ticket_data['attachments'].append(file_path)

        tickets_data.append(ticket_data)

    return jsonify(tickets_data), 200


@app.route('/admin/register', methods=['POST'])
def register_admin():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    # Perform additional validations on email, name, password, and other relevant details

    if not email or not name or not password:
        return jsonify({'message': 'Email, name, and password are required.'}), 400

    # Check if the email is already registered
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'Email already registered.'}), 409

    # Create a new admin user
    admin = User(email=email, name=name, password=password, user_type='admin')
    db.session.add(admin)
    db.session.commit()

    return jsonify({'message': 'Admin user registered successfully.'}), 201





if __name__ == '__main__':
    with app.app_context():
        # db.drop_all()
        db.create_all()  # Create database tables
    app.run(debug=True)
