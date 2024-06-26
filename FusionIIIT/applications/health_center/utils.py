import json
from datetime import datetime, timedelta
from applications.globals.models import ExtraInfo
from django.core import serializers
from applications.filetracking.models import File
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation, DepartmentInfo
from django.http import HttpResponse, JsonResponse
from notification.views import  healthcare_center_notif
from .models import (Ambulance_request, Appointment, Complaint, Doctor, 
                     Expiry, Hospital, Hospital_admit, Medicine, 
                     Prescribed_medicine, Prescription, Doctors_Schedule,Pathologist_Schedule,
                     Stock, Announcements, SpecialRequest, Pathologist, medical_relief)
from applications.filetracking.sdk.methods import *

def datetime_handler(date):
    '''
        Checks datetime format
    '''
    if hasattr(date, 'isoformat'):
        return date.isoformat()
    else:
        raise TypeError

def compounder_view_handler(request):
    '''
        handles rendering of pages for compounder view
    '''

    # compounder response to patients feedback
    if 'feed_com' in request.POST:                                    
        pk = request.POST.get('com_id')
        feedback = request.POST.get('feed')
        Complaint.objects.select_related('user_id','user_id__user','user_id__department').filter(id=pk).update(feedback=feedback)
        data = {'feedback': feedback}
        return JsonResponse(data)

    elif 'end' in request.POST:
        pk = request.POST.get('id')
        Ambulance_request.objects.select_related('user_id','user_id__user','user_id__department').filter(id=pk).update(end_date=datetime.now())
        amb=Ambulance_request.objects.select_related('user_id','user_id__user','user_id__department').filter(id=pk)
        for f in amb:
            dateo=f.end_date
        data={'datenow':dateo}
        return JsonResponse(data)

    # return expired medicine and update db
    elif 'returned' in request.POST:                                     
        pk = request.POST.get('id')
        Expiry.objects.select_related('medicine_id').filter(id=pk).update(returned=True,return_date=datetime.now())
        qty=Expiry.objects.select_related('medicine_id').get(id=pk).quantity
        med=Expiry.objects.select_related('medicine_id').get(id=pk).medicine_id.id
        quantity=Stock.objects.get(id=med).quantity
        quantity=quantity-qty
        Stock.objects.filter(id=med).update(quantity=quantity)
        data={'status':1}
        return JsonResponse(data)

    # updating new doctor info in db    
    elif 'add_doctor' in request.POST:                                         
        doctor=request.POST.get('new_doctor')
        specialization=request.POST.get('specialization')
        phone=request.POST.get('phone')
        Doctor.objects.create(
        doctor_name=doctor,
        doctor_phone=phone,
        specialization=specialization,
        active=True
        )
        data={'status':1, 'doctor':doctor, 'specialization':specialization, 'phone':phone}
        return JsonResponse(data)
    
    # updating new pathologist info in db    
    elif 'add_pathologist' in request.POST:                                         
        doctor=request.POST.get('new_pathologist')
        specialization=request.POST.get('specialization')
        phone=request.POST.get('phone')
        Pathologist.objects.create(
        pathologist_name=doctor,
        pathologist_phone=phone,
        specialization=specialization,
        active=True
        )
        data={'status':1, 'pathologist_name':doctor, 'specialization':specialization, 'pathologist_phone':phone}
        return JsonResponse(data)
    
    # making announcements from compounder 
    elif 'add' in request.POST:                                         
        ven=request.POST.get('venue')
        announcement=request.POST.get('announcement')
        Announcement.objects.create(
        venue=ven,
        announcement=announcement,
        )
        data={ 'venue':ven, 'announcement':announcement }
        return JsonResponse(data)

    # remove doctor by changing active status
    elif 'remove_doctor' in request.POST:                              
        doctor=request.POST.get('doctor_active')
        Doctor.objects.filter(id=doctor).update(active=False)
        doc=Doctor.objects.get(id=doctor).doctor_name
        data={'status':1, 'id':doctor, 'doc':doc}
        return JsonResponse(data)
    
    # remove pathologist by changing active status
    elif 'remove_pathologist' in request.POST:                              
        doctor=request.POST.get('pathologist_active')
        Pathologist.objects.filter(id=doctor).update(active=False)
        doc=Pathologist.objects.get(id=doctor).pathologist_name
        data={'status':1, 'id':doctor, 'doc':doc}
        return JsonResponse(data)

    # discharge patients
    elif 'discharge' in request.POST:                                        
        pk = request.POST.get('discharge')
        Hospital_admit.objects.select_related('user_id','user_id__user','user_id__department','doctor_id').filter(id=pk).update(discharge_date=datetime.now())
        hosp=Hospital_admit.objects.select_related('user_id','user_id__user','user_id__department','doctor_id').filter(id=pk)
        for f in hosp:
            dateo=f.discharge_date
        data={'datenow':dateo, 'id':pk}
        return JsonResponse(data)

    elif 'add_stock' in request.POST:
        medicine = request.POST.get('medicine_id')
        threshold_a = request.POST.get('threshold_a')
        medicine_name = Stock.objects.get(id=medicine)
        qty = int(request.POST.get('quantity'))
        supplier=request.POST.get('supplier')
        expiry=request.POST.get('expiry_date')
        Expiry.objects.create(
            medicine_id=medicine_name,
            quantity=qty,
            supplier=supplier,
            expiry_date=expiry,
            date=datetime.now(),
        )
        quantity = (Stock.objects.get(id=medicine)).quantity
        quantity = quantity + qty
        Stock.objects.filter(id=medicine).update(quantity=quantity)
        Stock.objects.filter(id=medicine).update(threshold=threshold_a)
        data = {'status': 1}
        return JsonResponse(data)

    # edit schedule for doctors
    elif 'edit_1' in request.POST:                                             
        doctor = request.POST.get('doctor')
        day = request.POST.get('day')
        time_in = request.POST.get('time_in')
        time_out = request.POST.get('time_out')
        room = request.POST.get('room')
        schedule = Doctors_Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor, day=day)
        doctor_id = Doctor.objects.get(id=doctor)
        if schedule.count() == 0:
            Doctors_Schedule.objects.create(doctor_id=doctor_id, day=day, room=room,
                                    from_time=time_in, to_time=time_out)
        else:
            Doctors_Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor_id, day=day).update(room=room)
            Doctors_Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor_id, day=day).update(from_time=time_in)
            Doctors_Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor_id, day=day).update(to_time=time_out)
        data={'status':1}
        return JsonResponse(data)


    # remove schedule for a doctor
    elif 'rmv' in request.POST:  
        doctor = request.POST.get('doctor')
        
        day = request.POST.get('day')
        Doctors_Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor, day=day).delete()
        data = {'status': 1}
        return JsonResponse(data)
    
    
     # edit schedule for pathologists
    elif 'edit12' in request.POST:                                             
        doctor = request.POST.get('pathologist')
        day = request.POST.get('day')
        time_in = request.POST.get('time_in')
        time_out = request.POST.get('time_out')
        room = request.POST.get('room')
        pathologist_id = Pathologist.objects.get(id=doctor)
        schedule = Pathologist_Schedule.objects.select_related('pathologist_id').filter(pathologist_id=doctor, day=day)
        if schedule.count() == 0:
            Pathologist_Schedule.objects.create(pathologist_id=pathologist_id, day=day, room=room,
                                    from_time=time_in, to_time=time_out)
        else:
            Pathologist_Schedule.objects.select_related('pathologist_id').filter(pathologist_id=pathologist_id, day=day).update(room=room)
            Pathologist_Schedule.objects.select_related('pathologist_id').filter(pathologist_id=pathologist_id, day=day).update(from_time=time_in)
            Pathologist_Schedule.objects.select_related('pathologist_id').filter(pathologist_id=pathologist_id, day=day).update(to_time=time_out)
        data={'status':1}
        return JsonResponse(data)
    
    
    # remove schedule for a doctor
    elif 'rmv1' in request.POST:  
        doctor = request.POST.get('pathologist')
        
        day = request.POST.get('day')
        Pathologist_Schedule.objects.select_related('pathologist_id').filter(pathologist_id=doctor, day=day).delete()
        data = {'status': 1}
        return JsonResponse(data)
    

    elif 'add_medicine' in request.POST:
        medicine = request.POST.get('new_medicine')
        quantity = request.POST.get('new_quantity')
        threshold = request.POST.get('threshold')
        new_supplier = request.POST.get('new_supplier')
        new_expiry_date = request.POST.get('new_expiry_date')
        Stock.objects.create(
            medicine_name=medicine,
            quantity=quantity,
            threshold=threshold
        )
        medicine_id = Stock.objects.get(medicine_name=medicine)
        Expiry.objects.create(
            medicine_id=medicine_id,
            quantity=quantity,
            supplier=new_supplier,
            expiry_date=new_expiry_date,
            returned=False,
            return_date=None,
            date=datetime.now()
        )
        data = {'medicine':  medicine, 'quantity': quantity, 'threshold': threshold,
                'new_supplier': new_supplier, 'new_expiry_date': new_expiry_date  }
        return JsonResponse(data)

    elif 'admission' in request.POST:
        user = request.POST.get('user_id')
        user_id = ExtraInfo.objects.select_related('user','department').get(id=user)
        doctor = request.POST.get('doctor_id')
        doctor_id = Doctor.objects.get(id=doctor)
        admission_date = request.POST.get('admission_date')
        reason = request.POST.get('description')
        hospital_doctor = request.POST.get('hospital_doctor')
        hospital_id = request.POST.get('hospital_name')
        hospital_name = Hospital.objects.get(id=hospital_id)
        Hospital_admit.objects.create(
                user_id=user_id,
                doctor_id=doctor_id,
                hospital_name=hospital_name,
                admission_date=admission_date,
                hospital_doctor=hospital_doctor,
                discharge_date=None,
                reason=reason
            )
        user=user_id.user
        data={'status':1}
        return JsonResponse(data)

    elif 'medicine_name' in request.POST:
        app = request.POST.get('user')
        user = Appointment.objects.select_related('user_id','user_id__user','user_id__department','doctor_id','schedule','schedule__doctor_id').get(id=app).user_id
        quantity = int(request.POST.get('quantity'))
        days = int(request.POST.get('days'))
        times = int(request.POST.get('times'))
        medicine_id = request.POST.get('medicine_name')
        medicine = Stock.objects.get(id=medicine_id)
        Medicine.objects.create(
            patient=user,
            medicine_id=medicine,
            quantity=quantity,
            days=days,
            times=times
        )
        user_medicine = Medicine.objects.filter(patient=user)
        list = []
        for med in user_medicine:
            list.append({'medicine': med.medicine_id.medicine_name, 'quantity': med.quantity,
                            'days': med.days, 'times': med.times})
        sches = json.dumps(list, default=datetime_handler)
        return HttpResponse(sches, content_type='json')
    
    elif 'medicine_name_b' in request.POST:
        user_id = request.POST.get('user')
        user = ExtraInfo.objects.select_related('user','department').get(id=user_id)
        quantity = int(request.POST.get('quantity'))
        days = int(request.POST.get('days'))
        times = int(request.POST.get('times'))
        medicine_id = request.POST.get('medicine_name_b')
        medicine = Stock.objects.get(id=medicine_id)
        Medicine.objects.create(
            patient=user,
            medicine_id=medicine,
            quantity=quantity,
            days=days,
            times=times
        )
        schs = Medicine.objects.filter(patient=user)
        list = []
        for s in schs:
            list.append({'medicine': s.medicine_id.medicine_name, 'quantity': s.quantity,
                            'days': s.days, 'times': s.times})
        sches = json.dumps(list, default=datetime_handler)
        return HttpResponse(sches, content_type='json')
    
    elif 'doct' in request.POST:
        doctor_id = request.POST.get('doct')
        schedule = Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor_id)
        list = []
        for s in schedule:
            list.append({'room': s.room, 'id': s.id, 'doctor': s.doctor_id.doctor_name,
                            'day': s.get_day_display(), 'from_time': s.from_time,
                            'to_time': s.to_time})

        sches = json.dumps(list, default=datetime_handler)
        return HttpResponse(sches, content_type='json')

    elif 'prescribe' in request.POST:
        app_id = request.POST.get('user')
        details = request.POST.get('details')
        tests = request.POST.get('tests')
        appointment = Appointment.objects.select_related('user_id','user_id__user','user_id__department','doctor_id','schedule','schedule__doctor_id').get(id=app_id)
        user=appointment.user_id
        doctor=appointment.doctor_id
        Prescription.objects.create(
            user_id=user,
            doctor_id=doctor,
            details=details,
            date=datetime.now(),
            test=tests,
            appointment=appointment
        )
        query = Medicine.objects.select_related('patient','patient__user','patient__department').objects.filter(patient=user)
        prescribe = Prescription.objects.select_related('user_id','user_id__user','user_id__department','doctor_id','appointment','appointment__user_id','appointment__user_id__user','appointment__user_id__department','appointment__doctor_id','appointment__schedule','appointment__schedule__doctor_id').objects.all().last()
        for medicine in query:
            medicine_id = medicine.medicine_id
            quantity = medicine.quantity
            days = medicine.days
            times = medicine.times
            Prescribed_medicine.objects.create(
                prescription_id=prescribe,
                medicine_id=medicine_id,
                quantity=quantity,
                days=days,
                times=times
            )
            today=datetime.now()
            expiry=Expiry.objects.select_related('medicine_id').filter(medicine_id=medicine_id,quantity__gt=0,returned=False,expiry_date__gte=today).order_by('expiry_date')
            stock=Stock.objects.get(medicine_name=medicine_id).quantity
            if stock>quantity:
                for e in expiry:
                    q=e.quantity
                    em=e.id
                    if q>quantity:
                        q=q-quantity
                        Expiry.objects.select_related('medicine_id').filter(id=em).update(quantity=q)
                        qty = Stock.objects.get(medicine_name=medicine_id).quantity
                        qty = qty-quantity
                        Stock.objects.filter(medicine_name=medicine_id).update(quantity=qty)
                        break
                    else:
                        quan=Expiry.objects.select_related('medicine_id').get(id=em).quantity
                        Expiry.objects.select_related('medicine_id').filter(id=em).update(quantity=0)
                        qty = Stock.objects.get(medicine_name=medicine_id).quantity
                        qty = qty-quan
                        Stock.objects.filter(medicine_name=medicine_id).update(quantity=qty)
                        quantity=quantity-quan
                status = 1
            else:
                status = 0
            Medicine.objects.select_related('patient','patient__user','patient__department').all().delete()

        healthcare_center_notif(request.user, user.user, 'presc')
        data = {'status': status, 'stock': stock}
        return JsonResponse(data)
    elif 'prescribe_b' in request.POST:
        user_id = request.POST.get('user')
        user = ExtraInfo.objects.select_related('user','department').get(id=user_id)
        doctor_id = request.POST.get('doctor')
        if doctor_id == "":
            doctor = None
        else:
            doctor = Doctor.objects.get(id=doctor_id)
        details = request.POST.get('details')
        tests = request.POST.get('tests')
        # app = Appointment.objects.select_related('user_id','user_id__user','user_id__department','doctor_id','schedule','schedule__doctor_id').filter(user_id=user_id,date=datetime.now())
        # if app:
        #     appointment = Appointment.objects.select_related('user_id','user_id__user','user_id__department','doctor_id','schedule','schedule__doctor_id').get(user_id=user_id,date=datetime.now())
        # else:
        #     appointment = None
        designation=request.POST.get('user')
        uploaded_file = request.FILES.get('file')
        d = HoldsDesignation.objects.get(user__username=designation)
        form_object=Prescription(
            user_id=user,
            doctor_id=doctor,
            details=details,
            date=datetime.now(),
            test=tests,          
            # appointment=appointment
        )
        form_object.save()
        request_object = Prescription.objects.get(pk=form_object.pk)
        send_file_id = create_file(
            uploader=request.user.username,
            uploader_designation=request.session['currentDesignationSelected'],
            receiver=designation,
            receiver_designation=d.designation,
            src_module="health_center",
            src_object_id=str(request_object.id),
            file_extra_JSON={"value": 2},
            attached_file=uploaded_file  
        )
        request_object.file_id=send_file_id
        request_object.save()
        
        query = Medicine.objects.select_related('patient','patient__user','patient__department').filter(patient=user)
        prescribe = Prescription.objects.select_related('user_id','user_id__user','user_id__department','doctor_id').all().last()
        for medicine in query:
            medicine_id = medicine.medicine_id
            quantity = medicine.quantity
            days = medicine.days
            times = medicine.times
            Prescribed_medicine.objects.create(
                prescription_id=prescribe,
                medicine_id=medicine_id,
                quantity=quantity,
                days=days,
                times=times
            )
            today=datetime.now()
            expiry=Expiry.objects.select_related('medicine_id').filter(medicine_id=medicine_id,quantity__gt=0,returned=False,expiry_date__gte=today).order_by('expiry_date')
            stock=Stock.objects.get(medicine_name=medicine_id).quantity
            if stock>quantity:
                for e in expiry:
                    q=e.quantity
                    em=e.id
                    if q>quantity:
                        q=q-quantity
                        Expiry.objects.select_related('medicine_id').filter(id=em).update(quantity=q)
                        qty = Stock.objects.get(medicine_name=medicine_id).quantity
                        qty = qty-quantity
                        Stock.objects.filter(medicine_name=medicine_id).update(quantity=qty)
                        break
                    else:
                        quan=Expiry.objects.select_related('medicine_id').get(id=em).quantity
                        Expiry.objects.select_related('medicine_id').filter(id=em).update(quantity=0)
                        qty = Stock.objects.get(medicine_name=medicine_id).quantity
                        qty = qty-quan
                        Stock.objects.filter(medicine_name=medicine_id).update(quantity=qty)
                        quantity=quantity-quan
                status = 1

            else:
                status = 0
            Medicine.objects.select_related('patient','patient__user','patient__department').all().delete()
          

        healthcare_center_notif(request.user, user.user, 'presc')
        data = {'status': status}
        return JsonResponse(data)
    elif 'cancel_presc' in request.POST:
        presc_id = request.POST.get('cancel_presc')
        prescription=Prescription.objects.filter(pk=presc_id)
        is_deleted = delete_file(id=presciption.file_id)
        prescription.delete()
        
        
        data = {'status': 1}
        return JsonResponse(data)
    elif 'medicine' in request.POST:
        med_id = request.POST.get('medicine')
        thresh = Stock.objects.get(id=med_id).threshold
        data = {'thresh': thresh}
        return JsonResponse(data)
    elif 'compounder_forward' in request.POST:
        acc_admin_des_id = Designation.objects.get(name="Accounts Admin")        
        user_ids = HoldsDesignation.objects.filter(designation_id=acc_admin_des_id.id).values_list('user_id', flat=True)    
        acc_admins = ExtraInfo.objects.get(user_id=user_ids[0])
        user=ExtraInfo.objects.get(pk=acc_admins.id)
        forwarded_file_id=forward_file(
            file_id=request.POST['file_id'],
            receiver=acc_admins.id, 
            receiver_designation="Accounts Admin",
            file_extra_JSON= {"value": 2},            
            remarks="Forwarded File with id: "+ str(request.POST['file_id'])+"to Accounts Admin "+str(acc_admins.id), 
            file_attachment=None,
        )
       
        medical_relief_instance = medical_relief.objects.get(file_id=request.POST['file_id'])        
        medical_relief_instance.compounder_forward_flag = True
        medical_relief_instance.save()
        
        healthcare_center_notif(request.user,user.user,'rel_approve')
        
        

       
        data = {'status': 1}
        return JsonResponse(data)
        
        
        
        


def student_view_handler(request):
    if 'amb_submit' in request.POST:
        user_id = ExtraInfo.objects.select_related('user','department').get(user=request.user)
        comp_id = ExtraInfo.objects.select_related('user','department').filter(user_type='compounder')
        reason = request.POST.get('reason')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        if end_date == '':
            end_date = None
        Ambulance_request.objects.create(
                user_id=user_id,
                date_request=datetime.now(),
                start_date=start_date,
                end_date=end_date,
                reason=reason
            )
        data = {'status': 1}
        healthcare_center_notif(request.user, request.user, 'amb_request')
        for cmp in comp_id:
                healthcare_center_notif(request.user, cmp.user, 'amb_req')

        return JsonResponse(data)
    elif "amb_submit1" in request.POST:
        user_id = ExtraInfo.objects.select_related('user','department').get(user=request.user)
        comp_id = ExtraInfo.objects.select_related('user','department').filter(user_type='compounder')
        doctor_id = request.POST.get('doctor')
        doctor = Doctor.objects.get(id=doctor_id)
        date = request.POST.get('date')
        schedule = Schedule.objects.select_related('doctor_id').get(id=date)
        datei = schedule.date
        app_time = schedule.to_time
        description = request.POST.get('description')
        Appointment.objects.create(
            user_id=user_id,
            doctor_id=doctor,
            description=description,
            schedule=schedule,
            date=datei
        )
        data = {
                'app_time': app_time, 'dt': datei , 'status' : 1
                }
        healthcare_center_notif(request.user, request.user, 'appoint')
        for cmp in comp_id:
                healthcare_center_notif(request.user, cmp.user, 'appoint_req')

        return JsonResponse(data)
    
    
    elif 'doctor' in request.POST:
        doctor_id = request.POST.get('doctor')
        days =Dotors_Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor_id).values('day')
        today = datetime.today()
        time = datetime.today().time()
        sch = Doctors_Schedule.objects.select_related('doctor_id').filter(date__gte=today)

        for day in days:
            for i in range(0, 7):
                date = (datetime.today()+timedelta(days=i)).date()
                dayi = date.weekday()
                d = day.get('day')
                if dayi == d:

                    Doctors_Schedule.objects.select_related('doctor_id').filter(doctor_id=doctor_id, day=dayi).update(date=date)

        sch.filter(date=today, to_time__lt=time).delete()
        schedule = sch.filter(doctor_id=doctor_id).order_by('date')
        schedules = serializers.serialize('json', schedule)
        return HttpResponse(schedules, content_type='json')
    
    
    elif 'feed_submit' in request.POST:
        user_id = ExtraInfo.objects.select_related('user','department').get(user=request.user)
        feedback = request.POST.get('feedback')
        Complaint.objects.create(
            user_id=user_id,
            complaint=feedback,
            date=datetime.now()
        )
        data = {'status': 1}
        return JsonResponse(data)
    elif 'cancel_amb' in request.POST:
        amb_id = request.POST.get('cancel_amb')
        Ambulance_request.objects.select_related('user_id','user_id__user','user_id__department').filter(pk=amb_id).delete()
        data = {'status': 1}
        return JsonResponse(data)
    elif 'cancel_app' in request.POST:
        app_id = request.POST.get('cancel_app')
        Appointment.objects.select_related('user_id','user_id__user','user_id__department','doctor_id','schedule','schedule__doctor_id').filter(pk=app_id).delete()
        data = {'status': 1}
        return JsonResponse(data)
    elif 'medical_relief_submit' in request.POST:
        designation = request.POST.get('designation')
        # print("# #")
        # print(designation)
        user=ExtraInfo.objects.get(pk=designation)
        description = request.POST.get('description')
        
        # Retrieve the uploaded file from request.FILES
        uploaded_file = request.FILES.get('file')

        # Create an instance of the medical_relief model
        form_object = medical_relief(
            description=description,
            file=uploaded_file
        )

        # Save the form object
        form_object.save()
        
        # Retrieve the form object you just saved
        request_object = medical_relief.objects.get(pk=form_object.pk)
        
        # Retrieve HoldsDesignation instances
        d = HoldsDesignation.objects.get(user__username=designation)
        d1 = HoldsDesignation.objects.get(user__username=request.user)

        # Create a file entry using the create_file utility function
        send_file_id = create_file(
            uploader=request.user.username,
            uploader_designation=request.session['currentDesignationSelected'],
            receiver=designation,
            receiver_designation=d.designation,
            src_module="health_center",
            src_object_id=str(request_object.id),
            file_extra_JSON={"value": 2},
            attached_file=uploaded_file  
        )  
        healthcare_center_notif(request.user,user.user,'rel_forward')
        request_object.file_id = send_file_id
        request_object.save()
        
        # file_details_dict = view_file(file_id=send_file_id)    
        # print(file_details_dict)   
        return JsonResponse({'status': 1})
    
    elif 'acc_admin_forward' in request.POST:
        file_id=request.POST['file_id']
        rec=File.objects.get(id=file_id)
        des=Designation.objects.get(pk=rec.designation_id)      
        user=ExtraInfo.objects.get(pk=rec.uploader_id)
        
        forwarded_file_id=forward_file(
            file_id=request.POST['file_id'],
            receiver=rec.uploader_id, 
            receiver_designation=des.name,
            file_extra_JSON= {"value": 2},            
            remarks="Forwarded File with id: "+ str(request.POST['file_id'])+"to"+str(rec.id), 
            file_attachment=None,
        )
        medical_relief_instance = medical_relief.objects.get(file_id=request.POST['file_id'])        
        medical_relief_instance.acc_admin_forward_flag = True
        medical_relief_instance.save()
        
        healthcare_center_notif(request.user,user.user,'rel_approved')
        
        return JsonResponse({'status':1})
        
    
        