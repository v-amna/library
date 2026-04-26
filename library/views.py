from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
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

    today = timezone.localdate()
    unavailable_book_ids = set(
        Borrow.objects.filter(return_date__gte=today).values_list("book_id", flat=True)
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


"""
User borrow request for the staff to approve
"""


@login_required
def borrow_book(request, book_id):
    if request.method != "POST":
        return redirect("book_search")

    book = get_object_or_404(Book, id=book_id, is_active=True)
    today = timezone.localdate()

    if Borrow.objects.is_borrowed_by_user(user=request.user, book=book):
        messages.warning(request, "You already borrowed this book.")
        return redirect("book_search")

    book_unavailable = Borrow.objects.filter(book=book, return_date__gte=today).exists()
    if book_unavailable:
        messages.error(request, "This book is currently unavailable.")
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

    if "renewed_once" in (borrow.duration_details or ""):
        messages.warning(request, "This borrow has already been renewed once.")
        return redirect("my_borrows")

    # TODO: Fix this logic
    borrow.save(update_fields=["return_date", "duration_details"])

    messages.success(request, "Renewed for 7 more days.")
    return redirect("my_borrows")
