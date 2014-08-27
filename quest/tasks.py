#coding=utf-8
from time import sleep
from celery.task import task
from celery import current_task

from quest.solrhelper import QuestionSolr,AnswerSolr,UserSolr
from quest.models import Question,Answer
from account.models import User

@task()
def insert_solr(solrtype,**kwargs):
    """对象序列化问题尚未解决 json or pickle 目前使用传递字典代替"""
    sleep(2)
    solr=None
    obj=None
    try:
        if solrtype=="answer":
            solr=AnswerSolr()
            obj=Answer(**kwargs)
            #obj=Answer(id=id,content=content,question_id=question_id,user_id=user_id)
        elif solrtype=="question":
            solr=QuestionSolr()
            obj=Question(**kwargs)
        elif solrtype=="user":
            solr=UserSolr()
            obj=User(**kwargs)
        solr.add(obj)
        return True
    except Exception,e:
        print e
        return e

@task()
def delete_solr(solr,obj_id):
    solr.remove(obj_id)
    return "delete complete"



