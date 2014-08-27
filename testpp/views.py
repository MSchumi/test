from django.shortcuts import render
from django.http import HttpResponse
from testpp.tasks import add
import pysolr

# Create your views here.
from celery.decorators import task

def add1(request):
    add(100,50)
    return HttpResponse("add1")
@task
def add2(x,y):
    return x+y;
def test1(request):
    solr = pysolr.Solr('http://localhost:8080/solr/question', timeout=10)
    solr.add([
        {
        "id": "doc_1",
        "title": "A test document",
        },
        {
        "id": "doc_2",
        "title": "The Banana: Tasty or Dangerous?",
        },])
    results = solr.search('title:document')
    import pdb;pdb.set_trace()
    return HttpResponse("123")


