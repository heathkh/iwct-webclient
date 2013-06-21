from django.conf.urls import patterns, url

from webclient import views

urlpatterns = patterns('',
    url(r'^$', views.Index, name='index'),
    url(r'^setup_credentials/', views.SetupAwsCredentials, name='setup_credentials'),
    url(r'^workstations/', views.Workstations, name='workstations'),
    #url(r'^start/(?P<instance_id>i-[0-9a-fA-F]+)', views.Start, name='start'),
    url(r'^stop/(?P<instance_id>i-[0-9a-fA-F]+)', views.Stop, name='stop'),    
    url(r'^connect/(?P<instance_id>i-[0-9a-fA-F]+)', views.Connect, name='connect'),
    url(r'^create/', views.CreateWorkstation, name='create_workstation' ),
    url(r'^destroy/(?P<instance_id>i-[0-9a-fA-F]+)', views.Destroy, name='destroy_workstation'),
    

  
)