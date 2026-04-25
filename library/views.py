from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Book, Borrow


@login_required
def book_search(request):
    q = request.GET.get("q", "").strip()

    books = Book.objects.filter(is_active=True).select_related("author", "category")
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
            "books": books,
            "q": q,
            "unavailable_book_ids": unavailable_book_ids,
        },
    )


@login_required
def borrow_book(request, book_id):
    if request.method != "POST":
        return redirect("book_search")

    book = get_object_or_404(Book, id=book_id, is_active=True)
    today = timezone.localdate()

    already_borrowed = Borrow.objects.filter(
        user=request.user,
        book=book,
        return_date__gte=today,
    ).exists()
    if already_borrowed:
        messages.warning(request, "You already borrowed this book.")
        return redirect("book_search")

    book_unavailable = Borrow.objects.filter(book=book, return_date__gte=today).exists()
    if book_unavailable:
        messages.error(request, "This book is currently unavailable.")
        return redirect("book_search")

    due_date = today + timedelta(days=14)
    Borrow.objects.create(
        book=book,
        user=request.user,
        return_date=due_date,
        duration_details="14 days",
    )
    messages.success(request, "Book borrowed successfully.")
    return redirect("my_borrows")


@login_required
def my_borrows(request):
    borrows = (
        Borrow.objects.filter(user=request.user)
        .select_related("book", "book__author")
        .order_by("-issued_from")
    )
    today = timezone.localdate()

    return render(
        request,
        "library/my_borrows.html",
        {"borrows": borrows, "today": today},
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

    borrow.return_date = borrow.return_date + timedelta(days=7)
    borrow.duration_details = "14 days + renewed_once"
    borrow.save(update_fields=["return_date", "duration_details"])

    messages.success(request, "Renewed for 7 more days.")
    return redirect("my_borrows")
