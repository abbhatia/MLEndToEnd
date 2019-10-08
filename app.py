# -*- coding: utf-8 -*-
import os
os.environ['HDF5_DISABLE_VERSION_CHECK'] = '1'

import numpy as np
from keras.applications.resnet50 import preprocess_input, decode_predictions
from keras.preprocessing import image
from keras.applications.resnet50 import ResNet50
import stripe
import sys
import json
from flask import Flask, redirect, url_for, render_template, request, session
from scripts import helpers
from scripts import forms
from scripts import tabledef
from werkzeug import secure_filename
from keras import backend as K

app = Flask(__name__)
app.secret_key = os.urandom(12)  # Generic key for dev purposes only

# Setup the app with the config.py file
app.config.from_object('config')

stripe_keys = {
	'secret_key': "key1",
	'publishable_key': "key2"
}

stripe.api_key = stripe_keys['secret_key']




@app.route('/stripe', methods=['GET'])
def index():
    if session.get('logged_in'):
        return render_template('stripe.html', key=stripe_keys['publishable_key'])
    return redirect(url_for('login'))


@app.route('/charge', methods=['POST'])
def charge():
    if session.get('logged_in'):
        # Amount in cents
        amount = 500
        current_user = helpers.get_user()
        customer = stripe.Customer.create(email=current_user.email, source=request.form['stripeToken'])
        charge = stripe.Charge.create(
            customer=customer.id,
            amount=amount,
            currency='usd',
            description='Service Plan'
        )
        helpers.change_user(paid=1)
        # do anything else, like execute shell command to enable user's service on your app
    
        return render_template('charge.html', amount=amount)
    return redirect(url_for('login'))


@app.route('/uploaded', methods=['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
      f = request.files['file']
      f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
      path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
      model = ResNet50(weights='imagenet')
      img = image.load_img(path, target_size=(224, 224))
      x = image.img_to_array(img)
      x = np.expand_dims(x, axis=0)
      x = preprocess_input(x)
      preds = model.predict(x)
      preds_decoded = decode_predictions(preds, top=3)[0]
      K.clear_session()
      return render_template('uploaded.html', title='Success',  predictions=preds_decoded, user_image=f.filename)


# -------- Login ------------------------------------------------------------- #
@app.route('/', methods=['GET', 'POST'])
def login():
    if not session.get('logged_in'):
        form = forms.LoginForm(request.form)
        if request.method == 'POST':
            username = request.form['username'].lower()
            password = request.form['password']
            if form.validate():
                if helpers.credentials_valid(username, password):
                    session['logged_in'] = True
                    session['username'] = username
                    return json.dumps({'status': 'Login successful'})
                return json.dumps({'status': 'Invalid user/pass'})
            return json.dumps({'status': 'Both fields required'})
        return render_template('login.html', form=form)
    user = helpers.get_user()
    return render_template('stripe.html', user=user)


@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))


# -------- Signup ---------------------------------------------------------- #
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if not session.get('logged_in'):
        form = forms.LoginForm(request.form)
        if request.method == 'POST':
            username = request.form['username'].lower()
            password = helpers.hash_password(request.form['password'])
            email = request.form['email']
            if form.validate():
                if not helpers.username_taken(username):
                    helpers.add_user(username, password, email)
                    session['logged_in'] = True
                    session['username'] = username
                    return json.dumps({'status': 'Signup successful'})
                return json.dumps({'status': 'Username taken'})
            return json.dumps({'status': 'User/Pass required'})
        return render_template('login.html', form=form)
    return redirect(url_for('login'))


# -------- Settings ---------------------------------------------------------- #
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if session.get('logged_in'):
        if request.method == 'POST':
            password = request.form['password']
            if password != "":
                password = helpers.hash_password(password)
            email = request.form['email']
            helpers.change_user(password=password, email=email)
            return json.dumps({'status': 'Saved'})
        user = helpers.get_user()
        return render_template('settings.html', user=user)
    return redirect(url_for('login'))


# ======== Main ============================================================== #
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)