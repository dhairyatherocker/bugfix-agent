from cart import add_item

def test_independent_carts():
    a = add_item(1)
    b = add_item(2)
    assert a == [1]
    assert b == [2]

def test_existing_cart():
    assert add_item(3, [9]) == [9, 3]
