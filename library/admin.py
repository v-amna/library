from datetime import timedelta

from django.contrib.auth import get_permission_codename
from django.utils import timezone

from django.contrib import admin
from .models import Author, Book, Borrow, Category, Profile,DEFAULT_BOOK_BORROW_DURATION

# Register your models here.
admin.site.register(Profile)
admin.site.register(Author)
admin.site.register(Category)
admin.site.register(Book)


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
        queryset.update(
            issued_by=request.user,
            issued_from=timezone.now(),
            return_date=timezone.now() + timedelta(days=DEFAULT_BOOK_BORROW_DURATION),
        )
        self.message_user(request, "Books issued successfully.")

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