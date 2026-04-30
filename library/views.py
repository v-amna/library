from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config import settings
from .models import Book, Borrow


@login_required
def book_search(request):
    q = request.GET.get("q", "").strip()

    books = Book.objects.filter(is_active=True).select_related("author", "category")

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
        Book.objects.filter(is_active=True,stock__lt=0).values_list("id", flat=True)
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

    if Borrow.objects.is_borrowed_by_user(user=request.user, book=book):
        messages.warning(request, "You already borrowed this book.")
        return redirect("book_search")

    # Check if the total number of books borrowed is greater than or equal to the stock
    active_borrow_count = Borrow.objects.filter(
        book=book,
        return_date__gte=today,
        book__is_active=True).exclude( status__in=[Borrow.Status.returned,Borrow.Status.rejected]).count()

    if active_borrow_count >= book.stock:
        messages.error(request, "Sorry, This book is no more available.")
        return redirect("book_search")

    Borrow.objects.create(
        book=book,
        user=request.user,
    )
    messages.success(request, "Book borrow requested place, Please reach to any staff.")
    return redirect("my_borrows")


@login_required
def my_borrows(request):
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
def renew_borrow(request, borrow_id):
    if request.method != "POST":
        return redirect("my_borrows")

    borrow = get_object_or_404(Borrow, id=borrow_id, user=request.user)
    today = timezone.localdate()

    if borrow.return_date < today:
        messages.error(request, "Overdue books cannot be renewed from this page.")
        return redirect("my_borrows")

    if "renewed_once" in (borrow.notes or ""):
        messages.warning(request, "This borrow has already been renewed once.")
        return redirect("my_borrows")

    # TODO: Fix this logic
    borrow.save(update_fields=["return_date", "notes"])

    messages.success(request, "Renewed for 7 more days.")
    return redirect("my_borrows")


def check_username(request):
    username = request.GET.get("username", None)
    if not username:
        return JsonResponse({"available": False, "error": "Username not provided"}, status=400)

    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({"available": not exists})
