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


class BookListFilter(admin.SimpleListFilter):
    title = 'Stock status'
    parameter_name = 'stock'

    def lookups(self, request, model_admin):
        return (
            ('0', 'Out of stock'),
            ('1', 'In stock'),
        )

    def queryset(self, request, queryset):
        if self.value() == '0':
            return queryset.filter(stock=0)
        elif self.value() == '1':
            return queryset.filter(stock__gt=0)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('id', 'book_name', 'isbn', 'author', 'stock', 'shelf_details', 'category',
                    'is_active')
    search_fields = ['book_name', 'isbn', 'author']
    ordering = ['book_name', 'isbn', 'author', 'stock']
    list_filter = [BookListFilter, 'category', 'is_active', 'shelf_details']


@admin.register(Borrow)
class BorrowAdmin(admin.ModelAdmin):
    list_display = ('id','created_at', 'user', 'status', 'book__isbn', 'book__book_name', 'book__stock', 'issued_from',
                    'return_date', 'notes')
    readonly_fields = ('created_at', 'issued_by')
    ordering = ["created_at"]
    actions = ['make_approve_borrow','make_renew_borrow', 'make_return_borrow' ]
    search_fields = ['user__username', 'book__book_name', 'book__isbn']
    list_filter = ['status', 'issued_from', 'return_date']
    form = BorrowForm

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
            if borrow.status != borrow.Status.open:
                message = f"Borrow id: {borrow.id} could not be issued due to status: {borrow.get_status_display()}"
                self.message_user(request, message, level='warning')
                return
            borrow.issued_by = request.user
            borrow.issued_from = now
            borrow.return_date = now + timedelta(days=DEFAULT_BOOK_BORROW_DURATION)
            borrow.status = borrow.Status.issued
            borrow.save()
            count += 1
        self.message_user(request, f"Books issued successfully ({count} record(s))")

    @admin.action(
        permissions=['renew'],
        description='Renew book'
    )
    def make_renew_borrow(self, request, queryset):
        """
        Staff can renew the borrowed book. This will update the return_date field for the selected borrow records
        to the default duration in the settings
        """
        count = 0
        now = timezone.now()
        for borrow in queryset:
            if borrow.status not in [borrow.Status.issued, borrow.Status.renewed]:
                message = f"Borrow id: {borrow.id} could not be renewed due to status: {borrow.get_status_display()}"
                self.message_user(request, message, level='warning')
                return
            borrow.return_date = now + timedelta(days=DEFAULT_BOOK_BORROW_DURATION)
            borrow.status = borrow.Status.renewed
            borrow.notes = f"{borrow.notes}, renewed on: {now} by {request.user}" if borrow.notes else f"renewed on: {now} by {request.user}"
            borrow.save()
            count += 1

        self.message_user(request, f"Books renewed successfully ({count} record(s)).")

    @admin.action(
        permissions=['return'],
        description='Return the book'
    )
    def make_return_borrow(self, request, queryset):
        """
        Staff can return the borrowed book. This will update the return_date to today
        """
        count = 0
        now = timezone.now()
        for borrow in queryset:
            if borrow.status not in [borrow.Status.issued, borrow.Status.renewed]:
                message = f"Borrow id: {borrow.id} could not be renewed due to status: {borrow.get_status_display()}"
                self.message_user(request, message, level='warning')
                return
            borrow.return_date = now
            borrow.status = borrow.Status.returned
            borrow.save()
            count += 1

        self.message_user(request, f"Books returned successfully ({count} record(s)).")

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

    def has_return_permission(self, request):
        """
        Check if use has permission to return books.
        """
        opts = self.opts
        codename = get_permission_codename('return', opts)
        return request.user.has_perm(f"{opts.app_label}.{codename}")
