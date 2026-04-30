from datetime import date, timedelta
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Permission
from django.contrib.messages.storage.base import BaseStorage
from django.utils import timezone
from django.contrib.admin.sites import AdminSite
from library.models import Profile, Author, Category, Book, Borrow
from library.admin import BookAdmin, BorrowAdmin, BookListFilter


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser',
                                             password='password')
        self.author = Author.objects.create(author_name='Test Author')
        self.category = Category.objects.create(category_name='Test Category')
        self.book = Book.objects.create(
            book_name='Test Book',
            author=self.author,
            isbn='1234567890',
            category=self.category,
            stock=5
        )

    def test_profile_str(self):
        profile = Profile.objects.create(user=self.user)
        self.assertEqual(str(profile), 'testuser')

    def test_author_str(self):
        self.assertEqual(str(self.author), 'Test Author')

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Test Category')

    def test_book_str(self):
        self.assertEqual(str(self.book), 'Test Book')
        self.assertEqual(self.book.book_name, 'Test Book')
        self.assertEqual(self.book.author, self.author)
        self.assertEqual(self.book.category, self.category)
        self.assertEqual(self.book.isbn, '1234567890')
        self.assertEqual(self.book.stock, 5)

    def test_borrow_str(self):
        borrow = Borrow.objects.create(user=self.user, book=self.book)
        self.assertEqual(str(borrow), 'testuser -> Test Book')

    def test_borrow_manager_is_borrowed_by_user(self):
        self.assertFalse(
            Borrow.objects.is_borrowed_by_user(self.user, self.book))
        Borrow.objects.create(user=self.user, book=self.book,
                              status=Borrow.Status.open)
        self.assertTrue(
            Borrow.objects.is_borrowed_by_user(self.user, self.book))

    def test_borrow_save_stock_logic(self):
        # Test stock decreases when status changes from open to issued
        borrow = Borrow.objects.create(user=self.user, book=self.book,
                                       status=Borrow.Status.open)
        self.assertEqual(self.book.stock, 5)

        borrow.status = Borrow.Status.issued
        borrow.save()
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 4)

        # Test stock increases when status changes from issued to returned
        borrow.status = Borrow.Status.returned
        borrow.save()
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 5)


class AdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.user = User.objects.create_superuser(username='admin',
                                                  password='password',
                                                  email='admin@test.com')
        self.author = Author.objects.create(author_name='Test Author')
        self.category = Category.objects.create(category_name='Test Category')
        self.book_in_stock = Book.objects.create(
            book_name='In Stock Book',
            author=self.author,
            isbn='111',
            category=self.category,
            stock=5
        )
        self.book_out_of_stock = Book.objects.create(
            book_name='Out of Stock Book',
            author=self.author,
            isbn='222',
            category=self.category,
            stock=0
        )
        self.factory = RequestFactory()

    def test_book_list_filter(self):
        request = self.factory.get('/')
        request.user = self.user

        # Filter for in stock
        filter_in_stock = BookListFilter(request, {'stock': '1'}, Book,
                                         BookAdmin)
        qs = filter_in_stock.queryset(request, Book.objects.all())
        self.assertIn(self.book_in_stock, qs)
        self.assertNotIn(self.book_out_of_stock, qs)

        # Filter for out of stock
        filter_out_of_stock = BookListFilter(request, {'stock': '0'}, Book,
                                             BookAdmin)
        qs = filter_out_of_stock.queryset(request, Book.objects.all())
        self.assertIn(self.book_out_of_stock, qs)
        self.assertNotIn(self.book_in_stock, qs)

    def test_borrow_admin_actions(self):
        borrow = Borrow.objects.create(user=self.user, book=self.book_in_stock,
                                       status=Borrow.Status.open)
        borrow_admin = BorrowAdmin(Borrow, self.site)
        request = self.factory.get('/')
        request.user = self.user
        setattr(request, '_messages', BaseStorage(request))

        # Test make_approve_borrow
        borrow_admin.make_approve_borrow(request,
                                         Borrow.objects.filter(pk=borrow.pk))
        borrow.refresh_from_db()
        self.assertEqual(borrow.status, Borrow.Status.issued)
        self.assertEqual(borrow.issued_by, self.user)
        self.assertIsNotNone(borrow.issued_from)
        self.assertIsNotNone(borrow.return_date)

        # Test make_renew_borrow
        borrow_admin.make_renew_borrow(request,
                                       Borrow.objects.filter(pk=borrow.pk))
        borrow.refresh_from_db()
        self.assertEqual(borrow.status, Borrow.Status.renewed)
        self.assertIn('renewed on', borrow.notes)

        # Test make_return_borrow
        borrow_admin.make_return_borrow(request,
                                        Borrow.objects.filter(pk=borrow.pk))
        borrow.refresh_from_db()
        self.assertEqual(borrow.status, Borrow.Status.returned)

    def test_borrow_admin_permissions(self):
        borrow_admin = BorrowAdmin(Borrow, self.site)
        regular_user = User.objects.create_user(username='regular',
                                                password='password')
        request = self.factory.get('/')
        request.user = regular_user

        # Initially no permissions
        self.assertFalse(borrow_admin.has_issue_permission(request))
        self.assertFalse(borrow_admin.has_renew_permission(request))
        self.assertFalse(borrow_admin.has_return_permission(request))

        # Grant permissions
        issue_perm = Permission.objects.get(codename='issue_borrow')
        renew_perm = Permission.objects.get(codename='renew_borrow')
        return_perm = Permission.objects.get(codename='return_borrow')

        regular_user.user_permissions.add(issue_perm, renew_perm, return_perm)
        regular_user = User.objects.get(
            pk=regular_user.pk)  # Refresh user permissions cache
        request.user = regular_user

        # Now should have permissions
        # Note: BorrowAdmin uses get_permission_codename('issue', opts)
        # which defaults to 'issue_borrow' because the permission is defined
        # in Meta.permissions as ('issue_borrow', ...) Actually django's
        # get_permission_codename('issue', opts) returns 'issue_borrow'?
        # Let's check admin.py:
        # codename = get_permission_codename('issue', opts)
        # By default django codename for change is 'change_borrow'.
        # Custom permissions in Borrow model are: 'issue_borrow',
        # 'return_borrow', 'renew_borrow'.
        # get_permission_codename('issue', opts) will return 'issue_borrow'.

        self.assertTrue(borrow_admin.has_issue_permission(request))
        self.assertTrue(borrow_admin.has_renew_permission(request))
        self.assertTrue(borrow_admin.has_return_permission(request))
