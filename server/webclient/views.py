from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django import forms
from django.http import HttpResponseRedirect

from cirruscluster import core
from cirruscluster import workstation

import models
from boto import exception


def GetManager(request):
  iam_credentials = request.user.iamcredentials
  region = 'us-east-1'
  manager = workstation.Manager(region, iam_credentials.iam_key_id,
                                iam_credentials.iam_key_secret)
  return manager

def Index(request):
  context = {}
  return render(request, 'index.html', context)
  

@login_required(login_url='/accounts/login/')
def Workstations(request):
  # check if iam credentials are in DB
  iam_credentials = None
  try: 
   iam_credentials = request.user.iamcredentials
  except:
    pass
  
  # get IAM credentials, if needed using root AWS credentials
  if not iam_credentials:
    return HttpResponseRedirect('/setup_credentials') # Redirect after POST
  if not workstation.IAMUserReady(iam_credentials.iam_key_id, iam_credentials.iam_key_secret):
    return HttpResponseRedirect('/setup_credentials') # Redirect after POST
  
  # fetch the workstation info 
  manager = GetManager(request)
  instances = manager.ListInstances()
  context = {'instances': instances}
  return render(request, 'workstations.html', context)


@login_required(login_url='/accounts/login/')
def Stop(request, instance_id):
  instance_id = instance_id.encode('ascii', 'ignore')
  GetManager(request).StopInstance(instance_id)  
  return HttpResponseRedirect('/workstations')


@login_required(login_url='/accounts/login/')
def Connect(request, instance_id):
  instance_id = instance_id.encode('ascii', 'ignore')
  manager = GetManager(request)
  conn_config_data = manager.CreateRemoteSessionConfig(instance_id)
  response = HttpResponse(conn_config_data, content_type='application/nx-session')
  response['Content-Disposition'] = 'attachment; filename="connect.nxs"'
  return response


class DestroyConfirmForm(forms.Form):
  confirm = forms.CharField(max_length=100)
  
  def clean_confirm(self):
    data = self.cleaned_data['confirm']
    if data != "destroy":
      raise forms.ValidationError("You must enter 'destroy' to confirm destruction of this workstation.")
    return data
  
  
@login_required(login_url='/accounts/login/')
def Destroy(request, instance_id):
  form = DestroyConfirmForm() # An unbound form
  instance_id = instance_id.encode('ascii', 'ignore')
  if request.method == 'POST': # If the form has been submitted...
    form = DestroyConfirmForm(request.POST) # A form bound to the POST data
    if form.is_valid(): # All validation rules pass
      manager = GetManager(request)
      manager.TerminateInstance(instance_id)
      return HttpResponseRedirect('/workstations/') # Redirect after POST
  
  return render(request, 'destroy_workstation.html', {'instance_id': instance_id, 'form': form,})          


class SetupAwsCredentialsForm(forms.Form):
  aws_key_id = forms.CharField(max_length=100)
  aws_key_secret = forms.CharField(max_length=100)
 

def SetupAwsCredentials(request):
  form = SetupAwsCredentialsForm() # An unbound form
  key_id = None
  key_secret = None
  if request.method == 'POST': # If the form has been submitted...
    form = SetupAwsCredentialsForm(request.POST) # A form bound to the POST data
    if form.is_valid(): # All validation rules pass
      # Process the data in form.cleaned_data
      root_aws_id = form.cleaned_data['aws_key_id']
      root_aws_secret = form.cleaned_data['aws_key_secret']
      try:
        key_id, key_secret = workstation.InitCirrusIAMUser(root_aws_id, 
                                                           root_aws_secret)
      except exception.BotoServerError as e:
        print e
        pass
    
    if key_id and key_secret:    
      iam_credentials = models.IamCredentials(user=request.user, 
                                              iam_key_id=key_id, 
                                              iam_key_secret=key_secret )      
      iam_credentials.save()      
      return HttpResponseRedirect('/workstations') # Redirect after POST
  
  return render(request, 'setup_credentials.html', {'form': form,})   


class CreateWorkstationForm(forms.Form):
  name = forms.CharField(label="name", max_length=100, min_length = 3, help_text=u'Name you would like to use for your new workstation.',)
  INSTANCE_TYPE_CHOICES = (
    ('c1.xlarge', 'c1.xlarge'),  
  )
  instance_type = forms.ChoiceField(choices=INSTANCE_TYPE_CHOICES)
  

def CreateWorkstation(request):
  form = CreateWorkstationForm(initial={'name': 'my_workstation', 'instance_type': 'c1.xlarge'}) # An unbound form
  
  if request.method == 'POST': # If the form has been submitted...
    form = CreateWorkstationForm(request.POST) # A form bound to the POST data
    if form.is_valid(): # All validation rules pass
      # Process the data in form.cleaned_data
      name = form.cleaned_data['name']
      instance_type = form.cleaned_data['instance_type']
      manager = GetManager(request)
      ubuntu_release_name = 'precise'
      mapr_version = 'v2.1.3'
      success = False      
      try:
        manager.CreateInstance(name, 
                               instance_type,
                               ubuntu_release_name, 
                               mapr_version,
                               core.default_ami_release_name, 
                               core.default_ami_owner_id)
        success = True
      except RuntimeError as e:
        messages.error(request, '%s' % (e))
      
      if success:
        messages.success(request, 'A new workstation was created: %s' % (name))
        
      return HttpResponseRedirect('/workstations/') # Redirect after POST
  
  return render(request, 'create_workstation.html', {'form': form,})    



