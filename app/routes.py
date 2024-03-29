from flask import render_template, flash, redirect, request, session
import os.path
import os
import json
import uuid
import time
import datetime
import math

from app import app

from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, DateField, IntegerField, DecimalField
from wtforms.validators import DataRequired

import eodatadown.eodatadownsystemmain

CONFIG_FILE = "/bigdata/eodd_wales_ard/scripts/eodd/config/EODataDownBaseConfig_psql.json"
EODD_WEB_PATHS = {"LCL":"/bigdata/eodd_wales_ard/web", "GLB":"http://144.124.81.196/eoddweb"}

N_SCNS_PAGE = 24

class SelectDataForm(FlaskForm):
    end_date = DateField('End', validators=[DataRequired()], format='%Y-%m-%d', default=datetime.date(1980, 1, 1), description='End Date')
    start_date = DateField('Start', validators=[DataRequired()], format='%Y-%m-%d', default=datetime.date.today, description='Start Date')
    sensor_field = SelectField('Sensor', choices=[('Landsat', 'Landsat'), ('Sentinel-1', 'Sentinel-1'), ('Sentinel-2', 'Sentinel-2')] , validators=[DataRequired()], default='Landsat')
    cloud_cover_thres = IntegerField('Cloud Threshold (0-100 %)', validators=[DataRequired()], default=100, description='For optical sensors a cloud threshold as a percentage threshold can be provided.')
    north_bound = DecimalField('North', validators=[DataRequired()], default=0.0, description='Optional, provide a Northern Bound.')
    south_bound = DecimalField('South', validators=[DataRequired()], default=0.0, description='Optional, provide a Southern Bound.')
    east_bound = DecimalField('East', validators=[DataRequired()], default=0.0, description='Optional, provide a Eastern Bound.')
    west_bound = DecimalField('West', validators=[DataRequired()], default=0.0, description='Optional, provide a Western Bound.')
    go_submit = SubmitField('View Scenes')


@app.route('/')
@app.route('/index')
def index():
    form = SelectDataForm(request.form)
    return render_template('index.html', form=form)


@app.route('/imagelist', methods=['GET', 'POST'])
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
    if 'start_date' in form:
        # New Query.
        start_date = form['start_date']
        end_date = form['end_date']
        sensor_str = form['sensor_field']
        cloud_cover_thres = int(form['cloud_cover_thres'])
        if cloud_cover_thres < 0:
            cloud_cover_thres = 0
        elif cloud_cover_thres > 100:
            cloud_cover_thres = 100
        north_bound = float(form['north_bound'])
        south_bound = float(form['south_bound'])
        east_bound = float(form['east_bound'])
        west_bound = float(form['west_bound'])
        use_bounds = True
        if (north_bound == 0) and (south_bound == 0) and (east_bound == 0) and (west_bound == 0):
            use_bounds = False

        session['start_date'] = start_date
        session['end_date'] = end_date
        session['sensor_str'] = sensor_str
        session['cloud_cover_thres'] = cloud_cover_thres
        session['north_bound'] = north_bound
        session['south_bound'] = south_bound
        session['east_bound'] = east_bound
        session['west_bound'] = west_bound
        session['use_bounds'] = use_bounds
        session['page'] = 0
        disp_page = 0
    else:
        # Use existing query
        if ('start_date' in session) and ('end_date' in session) and ('sensor_str' in session):
            start_date = session['start_date']
            end_date = session['end_date']
            sensor_str = session['sensor_str']
            cloud_cover_thres = session['cloud_cover_thres']
            north_bound = session['north_bound']
            south_bound = session['south_bound']
            east_bound = session['east_bound']
            west_bound = session['west_bound']
            use_bounds = session['use_bounds']
        else:
            flash('Session did not have any query information, please run query again...')
            return redirect('/')
        disp_page = 0
        if not request.args.get("page"):
            if 'page' in session:
                disp_page = int(session['page'])
        else:
            disp_page = int(request.args.get('page'))

    start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')

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

    imgs_dict = dict()
    if found_sensor_obj:
        if use_bounds:
            bbox = [west_bound, east_bound, south_bound, north_bound]
            n_scns = sensor_obj.query_scn_records_date_bbox_count(start_date_obj, end_date_obj, bbox, valid=True,
                                                                  cloud_thres=cloud_cover_thres)
        else:
            n_scns = sensor_obj.query_scn_records_date_count(start_date_obj, end_date_obj, valid=True,
                                                             cloud_thres=cloud_cover_thres)
        if n_scns > 0:
            n_full_pages = math.floor(n_scns / N_SCNS_PAGE)
            remain_scns = n_scns - (n_full_pages * N_SCNS_PAGE)

            if n_full_pages > 0:
                start_rec = 0
                n_pg_scns = N_SCNS_PAGE
                if (disp_page >= 0) and (disp_page <= n_full_pages):
                    start_rec = disp_page * N_SCNS_PAGE
                    session['page'] = disp_page
                elif disp_page > n_full_pages:
                    start_rec = n_full_pages * N_SCNS_PAGE
                    n_pg_scns = remain_scns
                    session['page'] = n_full_pages
                    disp_page = n_full_pages

                if use_bounds:
                    bbox = [west_bound, east_bound, south_bound, north_bound]
                    scns = sensor_obj.query_scn_records_date_bbox(start_date_obj, end_date_obj, bbox, start_rec,
                                                                  n_pg_scns, valid=True, cloud_thres=cloud_cover_thres)
                else:
                    scns = sensor_obj.query_scn_records_date(start_date_obj, end_date_obj, start_rec, n_pg_scns,
                                                             valid=True, cloud_thres=cloud_cover_thres)
            else:
                if use_bounds:
                    bbox = [west_bound, east_bound, south_bound, north_bound]
                    scns = sensor_obj.query_scn_records_date_bbox(start_date_obj, end_date_obj, bbox, 0, remain_scns,
                                                                  valid=True, cloud_thres=cloud_cover_thres)
                else:
                    scns = sensor_obj.query_scn_records_date(start_date_obj, end_date_obj, 0, remain_scns,
                                                             valid=True, cloud_thres=cloud_cover_thres)

            for scn in scns:
                imgs_dict[scn.PID] = dict()
                if sensor_str == 'Landsat':
                    imgs_dict[scn.PID]['id'] = scn.Scene_ID
                    imgs_dict[scn.PID]['date'] = scn.Date_Acquired.strftime('%Y-%m-%d')
                elif sensor_str == 'Sentinel-1':
                    imgs_dict[scn.PID]['id'] = scn.Scene_ID
                    imgs_dict[scn.PID]['date'] = scn.Acquisition_Date.strftime('%Y-%m-%d')
                elif sensor_str == 'Sentinel-2':
                    imgs_dict[scn.PID]['id'] = scn.Granule_ID
                    imgs_dict[scn.PID]['date'] = scn.Sensing_Time.strftime('%Y-%m-%d')
                else:
                    flash('Something has gone wrong could not find the sensor specified.')
                    return redirect('/')

                qk_imgs = scn.ExtendedInfo["quicklook"]["quicklookimgs"]
                qk_sm_img = ''
                for qk_img in qk_imgs:
                    if '250px' in qk_img:
                        qk_sm_img = qk_img
                        break

                glb_qk_sm_img = qk_sm_img.replace(EODD_WEB_PATHS["LCL"], EODD_WEB_PATHS["GLB"])
                imgs_dict[scn.PID]['img'] = glb_qk_sm_img

            page_info = {"c_page": disp_page}
            if n_full_pages > 0:
                page_info['n_pages'] = n_full_pages
                if remain_scns > 0:
                    page_info['n_pages'] = n_full_pages + 1
            else:
                page_info['n_pages'] = 1

            if disp_page < page_info['n_pages']-1:
                page_info['n_page'] = disp_page + 1
            if disp_page > 0:
                page_info['p_page'] = disp_page - 1

            return render_template('imagelist.html', scns=imgs_dict, sensor=sensor_str, page_info=page_info)
        else:
            flash("Did not find any scenes within query parameters, please change and try again")
            return redirect('/')
    else:
        print("Error - didn't not find the sensor ({}) object.".format(sensor_str))
        flash('Something has gone wrong could not find the sensor ({}) specified.'.format(sensor_str))
        return redirect('/')

    flash('Should not have got here, some unspecified error, please try again.')
    return redirect('/')


@app.route('/quicklook', methods=['GET'])
def quicklook():
    if not request.args.get("scn"):
        flash('A scene was not specified.')
        return redirect('/imagelist')
    scn_id = request.args.get("scn")
    try:
        sys_main_obj = eodatadown.eodatadownsystemmain.EODataDownSystemMain()
        sys_main_obj.parse_config(CONFIG_FILE)
        sensor_sys_objs = sys_main_obj.get_sensors()
    except Exception as e:
        print(e)
        flash('Something has gone wrong either the database was found or there is an error with the configuration file.')
        return redirect('/')

    if 'sensor_str' in session:
        sensor_str = session['sensor_str']
    else:
        flash('Session did not have any query information, please run query again...')
        return redirect('/')

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
        try:
            scn_obj = sensor_obj.get_scn_record(scn_id)
        except Exception as e:
            print(e)
            print("Error - did not file the scene requested: ".format(sensor_str))
            flash('Something has gone wrong could not find the sensor ({}) specified.'.format(sensor_str))
            return redirect('/')

        scn_sen_id = ""
        if sensor_str == 'Landsat':
            scn_sen_id = scn_obj.Scene_ID
        elif sensor_str == 'Sentinel-1':
            scn_sen_id = scn_obj.Scene_ID
        elif sensor_str == 'Sentinel-2':
            scn_sen_id = scn_obj.Product_ID
        else:
            flash('Something has gone wrong could not find the sensor specified.')
            return redirect('/')

        qk_imgs = scn_obj.ExtendedInfo["quicklook"]["quicklookimgs"]
        qk_lrg_img = ''
        for qk_img in qk_imgs:
            if '1000px' in qk_img:
                qk_lrg_img = qk_img
                break
        glb_qk_lrg_img = qk_lrg_img.replace(EODD_WEB_PATHS["LCL"], EODD_WEB_PATHS["GLB"])

        return render_template('quicklook.html', scn=scn_sen_id, sensor=sensor_str, scn_img=glb_qk_lrg_img, scn_obj=scn_obj)
    else:
        print("Error - didn't not find the sensor ({}) object.".format(sensor_str))
        flash('Something has gone wrong could not find the sensor ({}) specified.'.format(sensor_str))
        return redirect('/')

    flash('Should not have got here, some unspecified error, please try again.')
    return redirect('/')


@app.route('/tilecache', methods=['GET'])
def tilecache():
    if not request.args.get("scn"):
        flash('A scene was not specified.')
        return redirect('/imagelist')
    scn_id = request.args.get("scn")
    try:
        sys_main_obj = eodatadown.eodatadownsystemmain.EODataDownSystemMain()
        sys_main_obj.parse_config(CONFIG_FILE)
        sensor_sys_objs = sys_main_obj.get_sensors()
    except Exception as e:
        print(e)
        flash('Something has gone wrong either the database was found or there is an error with the configuration file.')
        return redirect('/')

    if 'sensor_str' in session:
        sensor_str = session['sensor_str']
    else:
        flash('Session did not have any query information, please run query again...')
        return redirect('/')

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
        try:
            scn_obj = sensor_obj.get_scn_record(scn_id)
        except Exception as e:
            print(e)
            print("Error - did not file the scene requested: ".format(sensor_str))
            flash('Something has gone wrong could not find the sensor ({}) specified.'.format(sensor_str))
            return redirect('/')

        scn_sen_id = ""
        if sensor_str == 'Landsat':
            scn_sen_id = scn_obj.Scene_ID
        elif sensor_str == 'Sentinel-1':
            scn_sen_id = scn_obj.Scene_ID
        elif sensor_str == 'Sentinel-2':
            scn_sen_id = scn_obj.Product_ID
        else:
            flash('Something has gone wrong could not find the sensor specified.')
            return redirect('/')

        tc_lcl_path = scn_obj.ExtendedInfo["tilecache"]["tilecachepath"]
        tc_glb_path = tc_lcl_path.replace(EODD_WEB_PATHS["LCL"], EODD_WEB_PATHS["GLB"])

        vtif_lcl_path = scn_obj.ExtendedInfo["tilecache"]["visgtiff"]
        vtif_glb_path = vtif_lcl_path.replace(EODD_WEB_PATHS["LCL"], EODD_WEB_PATHS["GLB"])

        return render_template('tilecache.html', scn=scn_sen_id, sensor=sensor_str, scn_tc_path=tc_glb_path,
                               scn_vtif_path=vtif_glb_path, scn_obj=scn_obj)
    else:
        print("Error - didn't not find the sensor ({}) object.".format(sensor_str))
        flash('Something has gone wrong could not find the sensor ({}) specified.'.format(sensor_str))
        return redirect('/')

    flash('Should not have got here, some unspecified error, please try again.')
    return redirect('/')


@app.route('/background')
def background():
    return render_template('background.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')


