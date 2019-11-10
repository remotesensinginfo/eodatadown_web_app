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

import eodatadown.eodatadownsystemmain

CONFIG_FILE = "/bigdata/eodd_wales_ard/scripts/eodd/config/EODataDownBaseConfig_psql.json"

class SelectDataForm(FlaskForm):
    start_date = DateField('Start', validators=[Required()], format='%Y/%m/%d', default=datetime.date(1980, 1, 1), description='Start Date')
    end_date = DateField('End', validators=[Required()], format='%Y/%m/%d', default=datetime.date.today, description='End Date')
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
    try:
        sys_main_obj = eodatadown.eodatadownsystemmain.EODataDownSystemMain()
        sys_main_obj.parse_config(CONFIG_FILE)
        sensor_sys_objs = sys_main_obj.get_sensors()
    except Exception as e:
        print(e)
        flash('Something has gone wrong either the database was found or there is an error with the configuration file.')
        return redirect('/')
    
    form = request.form
    start_date = form['start_date']
    end_date = form['end_date']
    sensor_str = form['sensor_field']
    
    print(start_date)
    print(end_date)
    print(sensor_str)
    print("HERE - 5")
    
    sensor_obj = None
    found_sensor_obj = False
    for sensor_sys_obj in sensor_sys_objs:
        if (sensor_str == 'Landsat') and (sensor_sys_obj.get_sensor_name() == "LandsatGOOG"):
            sensor_obj = sensor_sys_obj
            found_sensor_obj = True
        elif (sensor_str == 'Sentinel-1') and (sensor_sys_obj.get_sensor_name() == "Sentinel1ASF"):
            sensor_obj = sensor_sys_obj
            found_sensor_obj = True
        elif (sensor_str == 'Sentinel-2') and (sensor_sys_obj.get_sensor_name() == "Sentinel2GOOG"):
            sensor_obj = sensor_sys_obj
            found_sensor_obj = True

    if found_sensor_obj:
        print("HERE - 6")
    else:
        print("Error - didn't not find the sensor object.")
        flash('Something has gone wrong could not find the sensor specfied.')
        return redirect('/')
    
    return render_template('imagelist.html')
