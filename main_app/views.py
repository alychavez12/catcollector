from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView, DetailView
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
# NOTE: class-based views are classes that create view function objects containing
# pre-defined controller logic commonly used for basic CRUD operations
# their main benefit is to provide convenience to developers
from .models import Cat, Toy, Photo
from .forms import FeedingForm
from django.contrib.auth.forms import UserCreationForm

import uuid
import boto3

S3_BASE_URL = 'https://s3.us-east-2.amazonaws.com/'
BUCKET ='djangocatcollectorproject'


# we use this file to define controller logic
# NOTE: each controller is defined using either a function or a class
# NOTE responses are returned from view functions
# NOTE: all views function take at least one required positional argument: request

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')


@login_required # NOTE: this decorator will redirect the user to the login page if they are not logged in
def cats_index(request):
    cats = Cat.objects.filter(user=request.user) # NOTE: only show cats belonging to the logged in user
    return render(request, 'cats/index.html', {'cats': cats})

# NOTE: url params are explicitly passed to view functions seperate from the request object
@login_required
def cat_detail(request, cat_id):
    cat = Cat.objects.get(id=cat_id)
    feeding_form = FeedingForm()
    # 1. Create a list of toys the cat has
    cat_toy_ids = cat.toy.all().values_list('id') # gives us a list of toys ids beloging to a cat
    # 2. create a list of toys that the cat doesn't have
    toys_cat_doesnt_have = Toy.objects.exclude(id__in=cat_toy_ids)
    return render(request, 'cats/detail.html', {
        'cat': cat, 
        'feeding_form': feeding_form,
        'toys': toys_cat_doesnt_have
    })

@login_required
def add_feeding(request, cat_id):
    # create a new model instance of feeding
    form = FeedingForm(request.POST) # {'meal': 'B', date: '2023-04-05', cat_id: None}
    # validate user input provided from form submission
    if form.is_valid():
       new_feeding = form.save(commit=False) # create an in-memory instance without saving to the database
       new_feeding.cat_id = cat_id # attach the associated cat's id to the cat_id attr
       new_feeding.save() # this will save a new feeding to the database
    # as long as form is valid we can associate the related cat to the new feeding
    # return a redirect response to the client
    return redirect('cat_detail', cat_id=cat_id)
@login_required
def assoc_toy(request, cat_id, toy_id):
    # NOTE: this is a many-to-many relationship
    #find the cat
    cat = Cat.objects.get(id=cat_id)
    # associate the toy
    cat.toy.add(toy_id) # accepts objects or object id or pk(id) of object
    # redirect back to the detail page
    return redirect('cat_detail', cat_id=cat_id)
@login_required
def unassoc_toy(request, cat_id, toy_id):
    # NOTE: this is a many-to-many relationship
    #find the cat
    cat = Cat.objects.get(id=cat_id)
    # associate the toy
    cat.toy.remove(toy_id) # accepts objects or object id or pk(id) of object
    # redirect back to the detail page
    return redirect('cat_detail', cat_id=cat_id)

def signup(request):
   # if POST requests
    error_message = ''
    if request.method == 'POST':
        # create a user in memory using the UserCreationForm(this way we can validate the form inputs)
        form = UserCreationForm(request.POST)
        # checking if the form inputs are valid
        if form.is_valid():
            # if valid save new user to the data base
            user = form.save()
            # login the new user
            login(request, user)
          # redirect to the cats index page
            return redirect('cats_index')
        # else: we generate an error message 'invalid input'
        else:
            print(form.errors)
            error_message = 'Invalid sign up - try again'
        # redirect back to signup page
            


    # GET requests
        # send an empty form to the client
    form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form, 'error': error_message })
    
def add_photo(request, cat_id):
    # attempt to collect photo submission from request
    photo_file = request.FILES.get('photo-file', None)
    # if photo file if present
    if photo_file:
    # setup a s3 client object - obj with methods for working with s3
        s3 = boto3.client('s3')
    # create a unique name for the photo file
        key = uuid.uuid4().hex[:6] + photo_file.name[photo_file.name.rfind('.'):]
       #try to upload file to aws s3
        try:
           s3.upload_fileobj(photo_file, BUCKET, key)
         # if successfull generate a unique url for the image
           url = f"{S3_BASE_URL}{BUCKET}/{key}"
         # save the url as a new instance of the photo model
         # * make sure we asociate the cat with the new photo intance 
           Photo.object.create(url=url, cat_id=cat_id)
       # if there an exception (error)
        except Exception as error:
            print('photo upload error', error)
    return redirect('cat_detail', cat_id=cat_id)

         # print the error message for debugging
    # redirect to the detail page regardless if successfull or not

class CatCreate(LoginRequiredMixin, CreateView):
    model = Cat
    fields = ('name', 'breed', 'description', 'age') # adds all the fields to the corresponding ModelForm
    template_name = 'cats/cat_form.html'
    # success_url = '/cats/'

    def form_valid(self, form):
        form.instance.user = self.request.user# assign the logged in user to the cat
        return super().form_valid(form)# call the parent class's form_valid method


class CatUpdate(LoginRequiredMixin, UpdateView):
    model = Cat
    fields = ('description', 'age') # tuples are preferred over lists for the field attr
    template_name = 'cats/cat_form.html'
    # tuples are lightweight and use less space (memory)

class CatDelete(LoginRequiredMixin, DeleteView):
    model = Cat
    success_url = '/cats/'
    template_name = 'cats/cat_confirm_delete.html'

class ToyCreate(LoginRequiredMixin, CreateView):
    model = Toy
    fields = '__all__'
    template_name = 'toys/toy_form.html'

class ToyList(LoginRequiredMixin, ListView):
    model = Toy
    template_name = 'toys/toy_list.html'

class ToyDetail(LoginRequiredMixin, DetailView):
    model = Toy
    template_name = 'toys/toy_detail.html'
    
class ToyUpdate(LoginRequiredMixin, UpdateView):
    model = Toy
    fields = '__all__'
    template_name = 'toys/toy_form.html'

class ToyDelete(LoginRequiredMixin, DeleteView):
    model = Toy
    success_url = '/toys/'
    template_name = 'toys/toy_confirm_delete.html'