from flask import render_template, flash, redirect, request, session
import os.path
import os
import json
import uuid
import time
import datetime

from app import app

from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, DateField
from wtforms.validators import Required
#from wtforms.fields.html5 import DateField

class SelectDataForm(FlaskForm):
    start_date = DateField('Start', validators=[Required()], format='%d/%m/%Y', default=datetime.date(1980, 1, 1), description='Start Date')
    end_date = DateField('End', validators=[Required()], format='%d/%m/%Y', default=datetime.date.today, description='End Date')
    sensor_field = SelectField('Sensor', choices=[('Landsat', 'Landsat'), ('Sentinel-1', 'Sentinel-1'), ('Sentinel-2', 'Sentinel-2')] , validators=[Required()], default='Landsat')
    go_submit = SubmitField('Go')


@app.route('/')
@app.route('/index')
def index():
    form = SelectDataForm(request.form)
    print("HERE - 0")
    return render_template('index.html', form=form)


@app.route('/imagelist', methods=['POST'])
def imagelist():
    print("HERE - 3")
    form = request.form
    start_date = form['start_date']
    end_date = form['end_date']
    sensor = form['sensor_field']
    print("HERE - 5")
    return render_template('imagelist.html')