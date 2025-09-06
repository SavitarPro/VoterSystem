Install requiremnts from requirements.txt
(
	python -m venv venv
	venv\Scripts\activate
	pip install -r requirements.txt
)

Run Querries or create_database.py in database directory to create databases and tables.

Run main.py in ai_training directory to train and export AI models. (Face, Fingerprint) // Atleas 2 persons need to train the models

Copy exported Model files to appropriate model directory. (Face files to auth_service directory and Fingerprint files to vote_service directory)

Configure Database connection data in config.py of each service directory.

Run each service app.py in different Terminal
(Ex: 
	cd auth_service
	python app.py
)

Default user logins
admin_service
	admin
	admin123

fraud_service
	fraud_officer
	fraud123

registration_service
	admin
	admin123

