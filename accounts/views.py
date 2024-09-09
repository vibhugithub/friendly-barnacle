from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User, FriendRequest
from django.db.models import Q
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator


@login_required
def home_view(request):
    return render(request, "home.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def signup(request):
    if request.method == "POST":
        name = request.POST["name"]
        email = request.POST["email"].lower()
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password != confirm_password:
            return render(request, "signup.html", {"error": "Passwords do not match"})

        if User.objects.filter(email=email).exists():
            return render(request, "signup.html", {"error": "Email already exists"})

        User.objects.create(name=name, email=email, password=make_password(password))
        return redirect("login")

    return render(request, "signup.html")


def login_view(request):
    if request.method == "POST":
        email = request.POST["email"].lower()
        password = request.POST["password"]

        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            return redirect("home")
        else:
            return render(request, "login.html", {"error": "Invalid email or password"})

    return render(request, "login.html")


@login_required
def search_view(request):
    query = request.GET.get("search", "").strip()
    page_number = request.GET.get("page", 1)
    users = User.objects.none()

    if query:
        # Search by name or exact email match
        # users = User.objects.filter(Q(name__icontains=query) | Q(email__iexact=query))
        try:
            validate_email(query)
            messages.error(request, "Please enter a valid name, not an email.")
            return redirect("home")
        except ValidationError:
            # If it's not an email, proceed to search by name
            users = User.objects.filter(name__istartswith=query)

    # Friend requests sent and received by the current user
    sent_requests = FriendRequest.objects.filter(from_user=request.user)
    received_requests = FriendRequest.objects.filter(to_user=request.user)

    user_data = []
    for user in users:
        # print(user.id, user.name)
        has_sent_request = sent_requests.filter(
            to_user=user, status=FriendRequest.PENDING
        ).exists()
        has_received_request = received_requests.filter(
            from_user=user, status=FriendRequest.PENDING
        ).exists()
        is_friend = FriendRequest.objects.filter(
            (Q(from_user=request.user) & Q(to_user=user))
            | (Q(from_user=user) & Q(to_user=request.user)),
            status=FriendRequest.ACCEPTED,
        ).exists()
        user_data.append(
            {
                "user": user,
                "has_sent_request": has_sent_request,
                "has_received_request": has_received_request,
                "is_friend": is_friend,
            }
        )

    # Paginate the user_data list (after adding friend request statuses)
    paginator = Paginator(user_data, 10)  # Show 10 users per page
    page_obj = paginator.get_page(page_number)

    # for entry in page_obj:
    #     print(
    #         f"User: {entry['user'].name}, "
    #         f"User id: {entry['user'].id}, "
    #         f"Email: {entry['user'].email}, "
    #         f"Sent request: {entry['has_sent_request']}, "
    #         f"Received request: {entry['has_received_request']}, "
    #         f"Is friend: {entry['is_friend']}"
    #     )

    return render(
        request, "home.html", {"users": user_data, "page_obj": page_obj, "query": query}
    )


@login_required
def send_request(request, user_id):

    to_user = get_object_or_404(User, id=user_id)

    # Check if the user can send more friend requests
    if not request.user.can_send_friend_request():
        messages.error(
            request, "You have reached the limit for sending friend requests."
        )
        return redirect("home")

    if request.user == to_user:
        messages.error(request, "You cannot send a friend request to yourself.")
        return redirect("home")

    existing_request = FriendRequest.objects.filter(
        from_user=request.user, to_user=to_user
    ).first()
    if existing_request:
        if existing_request.status == FriendRequest.REJECTED:
            existing_request.status = FriendRequest.PENDING
            existing_request.save()
            messages.success(request, f"Friend request sent again to {to_user.name}.")
        else:
            messages.error(request, "You have already sent a friend request.")
    else:
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
        messages.success(request, f"Friend request sent to {to_user.name}.")

    return redirect("home")


@login_required
def accept_request(request, request_id):
    friend_request = get_object_or_404(
        FriendRequest, id=request_id, to_user=request.user, status=FriendRequest.PENDING
    )
    if request.method == "POST":
        friend_request.from_user.friends.add(request.user)
        request.user.friends.add(friend_request.from_user)
        friend_request.status = FriendRequest.ACCEPTED
        friend_request.save()
        return redirect("home")

    return redirect("pending_request")


@login_required
def pending_requests(request):
    pending_requests = FriendRequest.objects.filter(
        to_user=request.user, status=FriendRequest.PENDING
    )
    return render(
        request, "pending_request.html", {"pending_requests": pending_requests}
    )


@login_required
def friends_list(request):
    friends = User.objects.filter(
        Q(
            sent_requests__to_user=request.user,
            sent_requests__status=FriendRequest.ACCEPTED,
        )
        | Q(
            received_requests__from_user=request.user,
            received_requests__status=FriendRequest.ACCEPTED,
        )
    ).distinct()
    return render(request, "friends.html", {"friends": friends})


@login_required
def reject_request(request, request_id):
    if request.method == "POST":
        try:
            friend_request = FriendRequest.objects.get(
                id=request_id, to_user=request.user, status=FriendRequest.PENDING
            )
            friend_request.status = FriendRequest.REJECTED
            friend_request.save()
            messages.success(request, "Friend request has been rejected.")
        except FriendRequest.DoesNotExist:
            messages.error(request, "No pending friend request to reject.")

    return redirect("pending_requests")


@login_required
def reject_friendlist(request):
    rejected_requests = FriendRequest.objects.filter(
        from_user=request.user, status=FriendRequest.REJECTED
    ).select_related("from_user", "to_user")

    return render(
        request, "reject_request.html", {"rejected_requests": rejected_requests}
    )
