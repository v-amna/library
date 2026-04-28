from datetime import timedelta

from django.contrib.auth import get_permission_codename
from django.utils import timezone
from django.contrib import admin

from .models import Author, Book, Borrow, Category, Profile, DEFAULT_BOOK_BORROW_DURATION
from .forms import BorrowForm

# Admin UI customization
admin.site.site_header = "Library Management System"
admin.site.site_title = "Library Management System Admin"
admin.site.index_title = "Welcome to Library Management System"

# Register your models here.
admin.site.register(Profile)


class BookInline(admin.TabularInline):
    model = Book


class CategoryInline(admin.TabularInline):
    model = Category


class AuthorInline(admin.TabularInline):
    model = Author


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['category_name']
    inlines = [BookInline]


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    search_fields = ['author_name']
    inlines = [BookInline]

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('book_name', 'isbn', 'author', 'stock', 'shelf_details', 'category', 'is_active')
    search_fields = [ 'book_name', 'isbn','author']
    ordering = ['book_name', 'isbn','author','stock']
    list_filter = ['stock', 'category', 'is_active','shelf_details']

# TODO:
#  - Add button renew,issue on borrow changeAction
@admin.register(Borrow)
class BorrowAdmin(admin.ModelAdmin):
    list_display = ('created_at','user', 'status', 'book__isbn', 'book__book_name', 'book__stock', 'issued_from', 'return_date', 'notes')
    readonly_fields = ('created_at','issued_by')
    ordering = ["created_at"]
    actions = ['make_approve_borrow']
    search_fields = ['user__username', 'book__book_name', 'book__isbn']
    list_filter = [ 'status', 'issued_from', 'return_date']

    @admin.action(
        permissions=['issue'],
        description='Issue books to user')
    def make_approve_borrow(self, request, queryset):
        """
        Staff can approve the borrow request, which will set the issued_by,
        issued_from, and return_date fields for the selected borrow records.
        The staff will hand over the book to the user after approval.
        """

        # Loop over selected Borrow instances and save each one so
        # instance-level logic save overrides runs correctly.
        count = 0
        now = timezone.now()
        for borrow in queryset:
            borrow.issued_by = request.user
            borrow.issued_from = now
            borrow.return_date = now + timedelta(days=DEFAULT_BOOK_BORROW_DURATION)
            borrow.status = borrow.Status.issued
            borrow.save()
            count += 1

        self.message_user(request, f"Books issued successfully ({count} record(s)).")

    def has_issue_permission(self, request):
        """
        Check if use has permission to issue books.
        """
        opts = self.opts
        codename = get_permission_codename('issue', opts)
        return request.user.has_perm(f"{opts.app_label}.{codename}")


    def has_renew_permission(self, request):
        """
        Check if use has permission to renew books.
        """
        opts = self.opts
        codename = get_permission_codename('renew', opts)
        return request.user.has_perm(f"{opts.app_label}.{codename}")
