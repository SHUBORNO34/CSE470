from app import app, db
from flask import render_template, request, redirect, url_for,flash,session,send_from_directory,abort,jsonify
from app.models import Items, Order,User,UserPreference, RatingReview,Wishlist,Cart
from sqlalchemy.sql import text,or_
from math import ceil


@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/show_products', methods=['GET'])
def show_products():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Query database to get movies for the current page
    products = Items.query.paginate(page=page, per_page=per_page)

    # Calculate total number of pages
    total_pages = ceil(products.total / per_page)

    return render_template('show_products.html', products=products, page=page, total_pages=total_pages)

    
@app.route('/product/<string:Item_ID>')
def product_page(Item_ID):
    # Retrieve the product details from the database based on the product ID
    product = Items.query.filter_by(Item_ID=Item_ID).first()
    if product is None:
        abort(404)
    
    product1 = Items.query.filter_by(Item_ID=Item_ID).first()
    ratings_reviews = RatingReview.query.filter_by(item_id=Item_ID).all()
    image_path = product1.pic
    return render_template('product.html', product=product,image_path=image_path,ratings_reviews=ratings_reviews)

@app.route('/product/<string:Item_ID>/rating_review', methods=['GET', 'POST'])
def product_rating_review(Item_ID):
    if request.method == 'POST':
        rating = request.form.get('rating')
        review = request.form.get('review')

        # Create a new entry for rating and review in the database
        rating_review = RatingReview(item_id=Item_ID, rating=rating, review=review)
        db.session.add(rating_review)
        db.session.commit()

        return redirect(url_for('product_page', Item_ID=Item_ID))
        #return 'Rating: {}, Review: {}'.format(rating, review)
    
    return render_template('rating_review.html', Item_ID=Item_ID)


@app.route('/search', methods=['GET'])
def search_products():
    # Get the search query from the request
    query = request.args.get('query', '')

    # Get filter options from the request
    price = request.args.get('price')
    category = request.args.get('category')
    item_star = request.args.get('item_star')

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Base query for products
    query_base = Items.query

    # Apply filters if provided
    if price:
        query_base = query_base.filter(Items.price <= int(price))
    if category:
        query_base = query_base.filter(Items.category.ilike(f'%{category}%'))
    if item_star:
        query_base = query_base.filter(Items.item_star >= int(item_star))

    # Filter products based on search query
    if query:
        # If both query and filters are provided, filter by both
        query_results = query_base.filter(or_(Items.name.ilike(f'%{query}%'), Items.item_desc.ilike(f'%{query}%')))
    else:
        # If only filters are provided, use filtered query
        query_results = query_base

    # Fetch unique categories from the database
    categories = Items.query.with_entities(Items.category).distinct().all()
    categories = [category[0] for category in categories]

    # Paginate the results
    products = query_results.paginate(page=page, per_page=per_page)

    # Calculate total number of pages
    total_pages = products.total // per_page + (products.total % per_page > 0)

    return render_template('show_products.html', products=products, page=page, total_pages=total_pages, categories=categories)

@app.route('/product_pic')
def product_pic():
    product1 = Items.query.filter_by(Item_ID='P10001').first()
    if product1 is None:
        abort(404)
    image_path = product1.pic
    return render_template('product_pic.html', image_path=image_path)



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        categories = request.form.getlist('categories[]')

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        for category in categories:
            preference = UserPreference(user_id=new_user.id, category=category)
            db.session.add(preference)
        db.session.commit()

        session['username'] = username
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            # Authentication successful, store user id in session
            #session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard', username=user.username))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # Retrieve username from session
    username = session.get('username')
    #user_id = session.get('user_id')
    if username:
        # Fetch user preferences
        user = User.query.filter_by(username=username).first()
        preferences = UserPreference.query.filter_by(user_id=user.id).all()
        
        # Extract categories from user preferences
        categories = [preference.category for preference in preferences]
        
        # Fetch recommended products based on user preferences
        recommended_products = Items.query.filter(Items.category.in_(categories)).order_by(Items.item_star.desc()).limit(5).all()

        #fetch user's wishlist items
        wishlist_items = Wishlist.query.filter_by(user_id=user.id).all()
        
        # Extract item IDs from wishlist items
        item_ids = [item.item_id for item in wishlist_items]
        
        # Fetch wishlist products based on item IDs
        wishlist_products = Items.query.filter(Items.Item_ID.in_(item_ids)).all()

        return render_template('dashboard.html', username=username, recommended_products=recommended_products,wishlist_products=wishlist_products)
    else:
        return redirect(url_for('login'))

    
@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if request.method == 'POST':
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        user_id = user.id # Corrected line

        # Check if the user is logged in
        if not user_id:
            flash('Please log in to add items to your wishlist.', 'error')
            return redirect(url_for('login'))

        # Get item ID from the form
        item_id = request.form.get('item_id')

        # Check if the item is already in the user's wishlist
        existing_wishlist_item = Wishlist.query.filter_by(user_id=user_id, item_id=item_id).first()
        if existing_wishlist_item:
            flash('Item is already in your wishlist', 'error')
        else:
            # Add the item to the user's wishlist
            wishlist_item = Wishlist(user_id=user_id, item_id=item_id)
            db.session.add(wishlist_item)
            db.session.commit()
            flash('Item added to wishlist successfully', 'success')

        return redirect(url_for('dashboard'))

@app.route('/remove_from_wishlist/<item_id>', methods=['POST'])
def remove_from_wishlist(item_id):
    if request.method == 'POST':
        # Retrieve the user's ID from the session
        username = session.get('username')

        if username:
            user = User.query.filter_by(username=username).first()
            
            if user:
                user_id = user.id
                
                # Check if the item exists in the user's wishlist
                wishlist_item = Wishlist.query.filter_by(user_id=user_id, item_id=item_id).first()
                if wishlist_item:
                    # Remove the item from the wishlist
                    db.session.delete(wishlist_item)
                    db.session.commit()
                    flash('Item removed from wishlist successfully', 'success')
                else:
                    flash('Item not found in your wishlist', 'error')
            else:
                flash('User not found', 'error')
        else:
            flash('Please log in to remove items from your wishlist.', 'error')

        return redirect(url_for('dashboard'))



@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()
    # Redirect the user to the login page or any other page you want
    return redirect(url_for('login'))



@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if request.method == 'POST':
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        user_id = user.id # Corrected line

        # Check if the user is logged in
        if not user_id:
            flash('Please log in to add items to your cart.', 'error')
            return redirect(url_for('login'))

        # Get item ID from the form
        item_id = request.form.get('item_id')

        # Check if the item is already in the user's wishlist
        existing_cart_item = Cart.query.filter_by(user_id=user_id, item_id=item_id).first()
        if existing_cart_item:
            flash('Item is already in your cart', 'error')
        else:
            # Add the item to the user's wishlist
            cart_item = Cart(user_id=user_id, item_id=item_id)
            db.session.add(cart_item)
            db.session.commit()
            flash('Item added to cart successfully', 'success')

        return redirect(url_for('product_page', Item_ID=item_id))
    

@app.route('/cart')
def cart():        
    username = session.get('username')
        #user_id = session.get('user_id')
    if username:
            # Fetch user preferences
            user = User.query.filter_by(username=username).first()

            #fetch user's wishlist items
            cart_items = Cart.query.filter_by(user_id=user.id).all()
            
            # Extract item IDs from wishlist items
            item_ids = [item.item_id for item in cart_items]
            
            # Fetch wishlist products based on item IDs
            cart_products = Items.query.filter(Items.Item_ID.in_(item_ids)).all()
            total_price = round(sum([(item.price) for item in cart_products]), 2)
            return render_template('cart.html', username=username,cart_products=cart_products,total_price=total_price)
    else:
            return redirect(url_for('product'))


@app.route('/remove_from_cart/<item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if request.method == 'POST':
        # Retrieve the user's ID from the session
        username = session.get('username')

        if username:
            user = User.query.filter_by(username=username).first()
            
            if user:
                user_id = user.id
                
                # Check if the item exists in the user's wishlist
                cart_item = Cart.query.filter_by(user_id=user_id, item_id=item_id).first()
                if cart_item:
                    # Remove the item from the wishlist
                    db.session.delete(cart_item)
                    db.session.commit()
                    flash('Item removed from cart successfully', 'success')
                else:
                    flash('Item not found in your cart', 'error')
            else:
                flash('User not found', 'error')
        else:
            flash('Please log in to remove items from your cart.', 'error')

        return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'username' not in session:
        flash('Please login to proceed to checkout', 'error')
        return redirect(url_for('login'))
    
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if request.method == 'POST':
        phone = request.form['phone']
        address = request.form['address']
        # Assuming cart_items and total_price calculation happens before this point
        cart_items = Cart.query.filter_by(user_id=user.id).all()
        total_price = sum(item.price for item in cart_items)  # You'll need to adjust based on your actual model

        # Create and save the order
        order = Order(user_id=user.id, phone=phone, address=address, total_price=total_price)
        db.session.add(order)
        db.session.commit()
        
        # Assuming redirection to a payment or confirmation page
        # return redirect(url_for('order_confirmation'))  # Assuming an order_confirmation function exists

    cart_items = Cart.query.filter_by(user_id=user.id).all()
    cart_products = [Items.query.filter_by(Item_ID=item.item_id).first() for item in cart_items]
    total_price = sum(item.price for item in cart_products)
    
    return render_template('checkout.html', user=user, cart_products=cart_products, total_price=total_price)


@app.route('/place_order', methods=['POST'])
def place_order():
    # Retrieve user_id from session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    user_id=user.id
    if user_id is None:
        # Redirect to login if user_id not found in session
        return redirect(url_for('login'))

    phone = request.form['phone']
    address = request.form['address']
    
    # Calculate total_price from cart items
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    total_price = sum(item.item.price for item in cart_items)  # Make sure this line matches your models

    # Correctly passing user_id to the Order constructor
    order = Order(user_id=user_id, phone=phone, address=address, total_price=total_price)
    db.session.add(order)
    
    # Retrieve cart items for the user
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    
    # Add items to the order and clear the cart
    for cart_item in cart_items:
        # Find the actual item instance based on cart_item.item_id
        item = Items.query.filter_by(Item_ID=cart_item.item_id).first()
        if item:
            order.items.append(item)
        
        # Remove the item from the cart
        db.session.delete(cart_item)
    
    db.session.commit()
    
    return redirect(url_for('order_confirmation', order_id=order.id))

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_confirmation.html', order=order)
