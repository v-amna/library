from django.urls import path
from . import views

urlpatterns = [
    path("books/", views.book_search, name="book_search"),
    path("borrow/<int:book_id>/", views.borrow_book, name="borrow_book"),
    path("my-borrows/", views.my_borrows, name="my_borrows"),
    path("renew/<int:borrow_id>/", views.renew_borrow, name="renew_borrow"),
    path("check-username/", views.check_username, name="check_username"),
]
