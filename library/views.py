from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta

from config import settings
from .models import Book, Borrow, DEFAULT_BOOK_BORROW_DURATION


def home_page(request):
    """
    View for home page with the latest 4 active books.
    """

    books = Book.objects.filter(is_active=True).order_by("-created_at")[:4]

    return render(
        request,
        "home.html",
        {
            "books": books
        }
    )


@login_required
def book_search(request):
    """
    View for searching books with pagination.
    """
    q = request.GET.get("q", "").strip()

    books = Book.objects.filter(is_active=True).select_related(
        "author", "category")

    paginator = Paginator(books, settings.DEFAULT_PAGINATION_LIMIT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if q:
        books = books.filter(
            Q(book_name__icontains=q)
            | Q(author__author_name__icontains=q)
            | Q(isbn__icontains=q)
            | Q(category__category_name__icontains=q)
        )

    paginator = Paginator(books, settings.DEFAULT_PAGINATION_LIMIT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Mark all books with stock less than 0 as unavailable.
    # To borrow.
    unavailable_book_ids = set(
        Book.objects.filter(is_active=True, stock__lt=0).values_list(
            "id", flat=True)
    )

    return render(
        request,
        "library/book_search.html",
        {
            "q": q,
            "unavailable_book_ids": unavailable_book_ids,
            "page_obj": page_obj,
        },
    )


@login_required
def borrow_book(request, book_id):
    """
    User borrow request for the staff to approve
    """
    if request.method != "POST":
        return redirect("book_search")

    book = get_object_or_404(Book, id=book_id, is_active=True)
    today = timezone.localdate()

    if Borrow.objects.is_borrowed_by_user(user=request.user,
                                          book=book):
        messages.warning(request, "You already borrowed this book.")
        return redirect("book_search")

    # Check if the total number of books borrowed is greater than
    # or equal to the stock
    active_borrow_count = Borrow.objects.filter(
        book=book,
        return_date__gte=today,
        book__is_active=True).exclude(
        status__in=[Borrow.Status.returned,
                    Borrow.Status.rejected]).count()

    if active_borrow_count >= book.stock:
        messages.error(request,
                       "Sorry, This book is no more available.")
        return redirect("book_search")

    Borrow.objects.create(
        book=book,
        user=request.user,
    )
    messages.success(request,
                     "Book borrow requested place, " +
                     "Please reach to any staff.")
    return redirect("my_borrows")


@login_required
def my_borrows(request):
    """
    View to display the current user's borrow history.
    """
    borrows = (
        Borrow.objects.filter(user=request.user)
        .select_related("book", "book__author")
        .order_by("-issued_from")
    )

    paginator = Paginator(borrows, settings.DEFAULT_PAGINATION_LIMIT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    today = timezone.localdate()

    return render(
        request,
        "library/my_borrows.html",
        {
            "today": today,
            "page_obj": page_obj,
        },
    )


@login_required
def cancel_borrow(request, borrow_id):
    """
    View for users to cancel their book borrow. Before approval, users can
    cancel their borrow request. After approval, users can only return the
    book.
    """
    if request.method != "POST":
        return redirect("my_borrows")
    borrow = get_object_or_404(Borrow, id=borrow_id,
                               user=request.user)

    if borrow.status != Borrow.Status.open:
        messages.error(request,
                       "Cannot cancel a borrow that is not pending.")
        return redirect("my_borrows")

    deleted_count, _ = borrow.delete()
    if deleted_count > 0:
        messages.success(request,
                         ("Cancelled the borrow request of " +
                          f"'{borrow.book.book_name}'."))
    else:
        messages.error(request,
                       "Failed to delete. Please contact admin.")
    return redirect("my_borrows")


@login_required
def renew_borrow(request, borrow_id):
    """
    View for users to request a renewal of their book borrow.

    A user can only renew a borrow that is not overdue for once, then later
    user needs to approach the staff to renew the book.

    The renewal period is fixed on the settings as constant.
    """
    if request.method != "POST":
        return redirect("my_borrows")

    borrow = get_object_or_404(Borrow, id=borrow_id,
                               user=request.user)
    if borrow.status == Borrow.Status.renewed:
        messages.warning(request,
                         ("This borrow has already been renewed once." +
                          " Please contact the staff."))
        return redirect("my_borrows")

    # If status is not issued, then the book cannot be renewed by staff.
    if borrow.status != Borrow.Status.issued:
        messages.error(request,
                       "This book cannot be renewed" +
                       "Please contact the staff.")
        return redirect("my_borrows")

    now = timezone.now()
    borrow.return_date = now + timedelta(
        days=DEFAULT_BOOK_BORROW_DURATION)

    borrow.status = borrow.Status.renewed
    borrow.notes += (", " if borrow.notes else "") + (
        f"renewed on: {now} by {request.user}(user)")

    borrow.save()

    messages.success(request,
                     f"Renewed for {DEFAULT_BOOK_BORROW_DURATION} more days.")
    return redirect("my_borrows")


def check_username(request):
    """
    AJAX view to check if a username is already taken.
    """
    username = request.GET.get("username", None)
    if not username:
        return JsonResponse(
            {"available": False, "error": "Username not provided"},
            status=400)

    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({"available": not exists})
