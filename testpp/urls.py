from django.conf.urls import patterns,url

urlpatterns=patterns('testpp.views',
        url(r'test/$','test1'),
        url(r'add/$','add1'),
        )
