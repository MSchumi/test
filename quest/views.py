#coding:utf-8
import uuid
import os
import json
import time
from datetime import *

from django.shortcuts import render,render_to_response,RequestContext
from django.http import HttpResponse,HttpResponseRedirect,Http404
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from django.template.loader import render_to_string
from django.template import loader

from PIL import Image

from quest.helper import *
from quest.models import Question,Topic,Answer,Comment,AnswerEvaluation,QustionFollow
from feed.models import Activity
from quest.signals import question_submit_done
from quest.solrhelper import QSolr,QuestionSolr,AnswerSolr,UserSolr
#from feed.helper import * 

#from django.utils import simplejson

def main(request):
    "主页面加载 如果用户登录并且有关注好友,则加载好友动态，否则加载回答数量最多的问题"
    if request.user.is_authenticated(): 
        activity_list=Activity.activityobjects.get_activity_list(request.user.id,page=1,pagecount=15)
        if len(activity_list["activity_list"])>0:
            return render_to_response("main.html",activity_list,context_instance=RequestContext(request))
    question_list= Question.questionobjects.get_questions()
    return render_to_response("main.html",{"questions":question_list},context_instance=RequestContext(request))

def submit_question(request):
    try:
        if request.method=="POST":
            question=Question()
            question.title=request.POST["title"]
            question.content=request.POST["content"]
            question.category=request.POST["category"]
            question.user=request.user
            if question.submit_question(request.user):
                return HttpResponse(str(question.id))
    except Exception,e:
        print e
        return HttpResponse()

@csrf_protect
def add_topic(request):
    try:
        if request.method=="POST":
            topic=Topic()
            topic.title=request.POST["title"]
            topic.addtime=date.today()
            topic.save()
            event_content={"id":topic.id,"title":topic.title}
            save_event(request.user.id,1,event_content,topic.id)
            return HttpResponse("添加完成")
    except Exception,e:
        print e

def query_topic(request):
    try:
        if request.method=="GET" and request.GET["q"]!=" ":
            topic_str=""
            topic_set=Topic.objects.filter(title__contains=request.GET["q"])
            if topic_set and len(topic_set)>0:
                for topic in topic_set:
                    topic_str+="\""+topic.title+"\","
                topic_str="["+topic_str[:-1]+"]"
                return HttpResponse(topic_str)
            else:
                return HttpResponse("[]")
        else:
            return HttpResponse("[]")
    except Exception ,e:
        print e

def get_hotquestion(request):
    try:
        if request.method=="GET":
            start=request.GET["start"]
            end=request.GET["end"]
            question_set=Question.objects.all()[start:end]
            q_str=""
            for question in question_set:
                q_str+="{\"title\":\""+question.title+"\",\"content\":\""+question.content.replace("\"","#")+"\"},"
            q_str="{\"items\":["+q_str[:-1]+"]}"
            return HttpResponse(q_str)
        else:
            return HttpResponse("{\"itens\":[]}")
    except Exception,e:
        print e

def get_questions1(request):
    try:
        if request.method=="GET": 
            question_list= Question.questionobjects.get_questions()
            #import pdb;pdb.set_trace()
            html_str=render_to_string("question_list.html",{"questions":question_list})
            return HttpResponse(html_str)
        else:
            return HttpResponse("22")
    except Exception,e:
        return None 

def show_question(request,question_id):
    question=None
    answers=None
    if request.user.is_authenticated():
        user_id=request.user.pk
        question=Question.objects.filter(id=question_id).extra(select={'followed':'select count(1) from quest_qustionfollow where\
                question_id=%d and user_id=%d'%(int(question_id),user_id)})  
        answers=Answer.answerobjects.get_answerlist(question_id,user_id)
    else:
        question=Question.objects.filter(id=question_id)
        answers=Answer.answerobjects.get_answerlist(question_id)
    if not question:
        raise Http404
    return render_to_response("question.html",{"question":question[0],"answers_list":answers},context_instance=RequestContext(request))
def get_question_info_by_id(request,question_id):
    question=Question.objects.filter(pk=question_id)

def add_answer(request):
    question_id=request.POST["questionid"]
    content=request.POST["content"]
    answer=Answer(user=request.user,question_id=question_id,content=content)
    answer.submit_answer(request.user)
    html_str=render_to_string('answerlist.html',{'answers_list':[answer]})
    return HttpResponse(html_str)

def get_answers_htmlstr(request,question_id):
    answers=Answer.answerobjects.get_answerlist(question_id,request.user.id)
    html_str=render_to_string('answerlist.html',{'answers_list':answers})
    return html_str

def get_answers(request,question_id):
    html_str=get_anwers_htmlstr(question_id)
    return HttpResponse(html_str)

def get_comment(request):
    "获取评论列表 加载更多尚未细化"
    answer_id=request.GET["answerid"]
    comments=Comment.objects.select_related('user','touser').filter(answer_id=answer_id)
    html_str=render_to_string("commentlist.html",{"comments_list":comments})
    return HttpResponse(html_str)

def add_comment(request):
    "添加评论"
    answer_id=request.POST["answerid"]
    question_id=request.POST["questionid"]
    content=request.POST["content"]
    touser_id=request.POST.get("touser",None)
    comment=Comment.objects.create(answer_id= answer_id,content=content,user=request.user,touser_id= touser_id)
    comment.answer.commentcount+=1
    comment.answer.save()
    html_str=render_to_string("commentlist.html",{"comments_list":[comment]})
    return HttpResponse(html_str)

def vote_answer(request):
    "用户对问题投票+表示新增-表示update 用户字投票问题尚未解决"
    answer_id=request.POST["answerid"]
    op_type=request.POST.get("type","+")
    status=int(request.POST["status"])
    is_exists=False
    if op_type!="+":
        evaluate=AnswerEvaluation.objects.select_related('answer').get(answer_id=answer_id,user_id=request.user.id)
        evaluate.cancel_vote(request.user,status)
    else:
        is_exists=False
        evaluate=AnswerEvaluation.objects.filter(answer_id=answer_id,user_id=request.user.id)
        if len(evaluate)>0:
            evaluate=evaluate[0]
            is_exists=True
        else:
            evaluate=AnswerEvaluation(answer_id=answer_id,user_id=request.user.id)
        evaluate.submit_vote(request.user,status,is_exists)
    return HttpResponse("ok")
    
@csrf_protect
def image_test(request):
    return render_to_response("image.html",context_instance=RequestContext(request))

def image_upload(request):
    "图片上传测试 现在废弃"
    reqfile = request.FILES['file1']
    img = Image.open(reqfile)
    img.thumbnail((500,500),Image.ANTIALIAS)
    if not os.path.exists("image"):
        os.mkdir("image")
    img.save("F:/F1/Question/image/c1.jpg")
    return HttpResponse("ok"+os.path.abspath("image"))

def follow_question(request):
    "关注问题"
    if request.method=="POST":
        qid=request.POST.get("qid",None)
        typecode=request.POST.get("type",None)
        if qid and typecode:
            if typecode=="0":
                follow=QustionFollow(question_id=qid,user_id=request.user.id)
                follow.follow_question(request.user)
            else:
                follow=QustionFollow.objects.filter(question_id=qid,user_id=request.user.id)[0]
                follow.cancel_follow(request.user)
            return HttpResponse()
        else:
            return Http404

def server_error(request,template_name="404.html"):
    "定义404页面"
    return render_to_response(template_name,context_instance=RequestContext(request))

def get_suggestions(request):
    "获取问题提示"
    if request.method=="GET":
        q=request.GET.get('q','')
        solr=QuestionSolr()
        docs=solr.suggestion(word=q)
        return HttpResponse(json.dumps(docs))
    else:
        return None

def search_results(request):
    "检索结果默认检索问题"
    if request.method=='GET':
        q=request.GET.get('q','')
        searchtype=request.GET.get('type','question')
        if searchtype=="user":
            solr=UserSolr()
        elif searchtype=="answer":
            solr=AnswerSolr()
        else:
            solr=QuestionSolr()
        data=solr.search_by_keyword(q)
        return render_to_response('search.html',{'searchword':q,'searchtype':searchtype,'data':data})
    return HttpResponse()




