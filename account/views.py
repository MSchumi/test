#coding:utf-8
import uuid
import time
import os
import json
from django.shortcuts import render,render_to_response,RequestContext
from django.http import HttpResponse,HttpResponseRedirect
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import authenticate,login,logout
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.conf import settings

from account.emailhelper import send_confirmemail
from account.models import User,Register_Temp,UserFollow
from quest.models import Event,EventContent
#from account.signals import register_user_done,follow_user_done
from account.helper import follow_user as helper_follow_user,create_user
from quest.solrhelper import UserSolr
import traceback

@csrf_protect
def index(request):
    return render_to_response('login.html',context_instance=RequestContext(request))

def register_user(request):
    if request.method=='POST':
        try:
            name=request.POST['name']
            surname=request.POST['surname']
            email=request.POST['email']
            password=request.POST['password']
            activecode=unicode(uuid.uuid5(uuid.NAMESPACE_DNS,email.encode('utf-8')))
            create_user(email=email,password=password,name=name,surname=surname,activecode=activecode)
            try:
                send_confirmemail(email,activecode,surname+name)
            except Exception,e:
                return HttpResponse(u'邮件发送失败')
            return HttpResponse(u'注册成功')
        except Exception,e:
            print traceback.print_exc()
            return HttpResponse(u'失败')

def login_user(request):
    try:
        email=request.POST['email']
        password=request.POST['password']
        user=authenticate(email=email,password=password)
        if user is not None:
            login(request,user)
            return HttpResponseRedirect('/question/')
        else:
            return HttpResponse(u'用户名密码错误')
    except Exception,e:
        print traceback.print_exc()
        return HttpResponse(u'异常')

def logout_user(request):
    try:
        logout(request)
        return HttpResponseRedirect("/account/?login")
    except Exception,e:
        print traceback.print_exc()
        return HttpResponse(u'异常')

def activate_user(request,activecode=None):
    try:
        info=Register_Temp.objects.filter(activecode=activecode)
        if activecode and info and len(info)>0:
            user=User.objects.get(email=info[0].email)
            user.is_active=True
            user.save()
            user=authenticate(email=info[0].email,auth_by_email=True)
            login(request,user)
            return HttpResponse(u'成功')
    except Exception,e:
        print traceback.print_exc()
        return HttpResponse(u'失败')

@csrf_protect
@login_required
def get_userinfo(request,userid):
    if not userid:
        userid=request.user.id;
        userinfo=request.user
    userinfo=User.objects.get(pk=userid)
    events=Event.eventobjects.get_event_list(userid)
    is_self=False
    is_followed=False
    if len(UserFollow.objects.filter(ufollow=request.user.id,tuser__id=userid))>0:
        is_followed=True
    if int(userid)==request.user.id:
        is_self=True
    return render_to_response("userinfo.html",{"events_list":events["event_list"],"statistics":events["statistics"],"userinfo":\
            userinfo,"is_self": is_self,"is_followed":is_followed},context_instance=RequestContext(request))

def follow_user(request): 
    try:
        if request.method=="POST":
            userid=request.POST.get("uid",None)
            ftype=request.POST.get('type',None)
            if userid and request.user.is_authenticated():
                helper_follow_user(userid,ftype,request.user)
        return HttpResponse("Ok")
    except Exception,e:
        print 
        return HttpResponse("error")

def upload_image(request):
    img=request.FILES.get("avat_file",None)
    if img:
        subdir="Image/"+time.strftime("%Y/%m/%d/",time.localtime())
        image_dir=settings.MEDIA_ROOT+subdir
        image_name=str(uuid.uuid1())+".jpg"
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        f=open(image_dir+image_name,"wb")
        f.write(img.read())
        f.close()
        script="<script type='text/javascript' >parent.show_avatar({'src':'"+settings.MEDIA_URL+subdir+image_name+"'})</script>'"
        return HttpResponse(script)
    else:
        return HttpResponse("error")

def change_image(request):
    img=request.FILES.get("avat_file",None)
    if img:
        subdir="Image/"+time.strftime("%Y/%m/%d/",time.localtime())
        image_dir=settings.MEDIA_ROOT+subdir
        image_name=str(uuid.uuid1())+".jpg"
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        f=open(image_dir+image_name,"wb")
        f.write(img.read())
        f.close()
        user=request.user
        user.avatar=settings.MEDIA_URL+subdir+image_name
        #user.avatar=img
        user.save()
        script="<script type='text/javascript' >parent.show_avatar({'src':'"+settings.MEDIA_URL+subdir+image_name+"'})</script>'"
        return HttpResponse(script)
    else:
        return HttpResponse("error")

def get_suggestions(request):
    if request.method=="GET":
        q=request.GET.get('q','')
        solr=UserSolr()
        #import pdb;pdb.set_trace()
        docs=solr.suggestion(word=q)
        return HttpResponse(json.dumps(docs))
    else:
        return None

    

