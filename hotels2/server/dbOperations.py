from hotels2.server.mongoConnection import *
from hotels2.models.hotel import Hotel
from hotels2.models.room import Room
from hotels2.models.customer import Customer
from datetime import datetime
from bson.objectid import ObjectId
from hotels2.models.validators import *
import re
from pprint import pprint

mongo = MongoConnection()


def add_validators():
    mongo.db.command("collMod", "Rooms", validator=room_validator)
    mongo.db.command("collMod", "Hotels", validator=hotel_validator)
    mongo.db.command("collMod", "Customers", validator=customer_validator)
    mongo.db.command("collMod", "Booking_Logs", validator=booking_logs_validator)


# ### Hotels methods ###
def add_hotel(name: str, street: str, city: str, zip_code: str, img: str):
    zip_regex = r"^\d{5}$"
    result = re.match(zip_regex, zip_code)

    if result:
        new_hotel = Hotel(name, street, city, zip_code, img)
        mongo.hotels.insert_one(vars(new_hotel))
        return True
    else:
        print("[SERVER] Invalid zip code format. The format is: xxxxx")
        return False


def remove_hotel(hotel_id: str):
    try:
        _id = ObjectId(hotel_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    res1 = mongo.hotels.delete_one({"_id": _id})
    res2 = mongo.rooms.delete_many({"hotel_id": _id})
    print("[SERVER] Removed:", res1.deleted_count, "hotels")
    print("[SERVER] Removed:", res2.deleted_count, "rooms")
    return True


def get_all_hotels():
    hotels = mongo.hotels.find()
    hotels = list(hotels)
    if not len(hotels):
        print("[SERVER] No hotels in the database.")
    return hotels


# ### Rooms methods ###
def add_room(hotel_id: str, room_type: int, room_number: int, ppn, img: str, availability: bool = True):
    try:
        _id = ObjectId(hotel_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    count = mongo.rooms.count_documents({"hotel_id": _id, "room_number": room_number})
    if count > 0:
        print("[SERVER] Room number", room_number, "already exists.")
        return False
    else:
        new_room = Room(_id, room_type, room_number, float(ppn), availability, img)
        mongo.rooms.insert_one(vars(new_room))
        return True


def remove_room(room_id: str):
    try:
        _id = ObjectId(room_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    res = mongo.rooms.delete_one({"_id": _id})
    print("[SERVER] Removed:", res.deleted_count, "elements")
    return True


def set_price_per_night(room_id: str, new_price):
    try:
        _id = ObjectId(room_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    price_update = {
        "$set": {"price_per_night": float(new_price)}
    }
    try:
        update = mongo.rooms.update_one({"_id": _id}, price_update)
        if update.matched_count <= 0:
            print("[SERVER] No room with such id")
            return False
        return True
    except Exception as e:
        print("[SERVER] Validation failed")
        pprint(e)
        return False


def set_availability(room_id: str, availability: bool):
    try:
        _id = ObjectId(room_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    availability_update = {
        "$set": {"is_available": availability}
    }
    update = mongo.rooms.update_one({"_id": _id}, availability_update)
    if update.matched_count <= 0:
        print("[SERVER] No room with such id")
        return False
    return True


# ### Customers methods ###
def add_customer(name: str, surname: str, mail: str, passwd: str):
    count = mongo.customers.count_documents({"email": mail})
    if count > 0:
        print("[SERVER] This email address is already taken.")
        return False
    new_customer = Customer(name, surname, mail, passwd)
    mongo.customers.insert_one(vars(new_customer))
    return True


def remove_customer(customer_id):
    try:
        _id = ObjectId(customer_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    res = mongo.customers.delete_one({"_id": _id})
    print("[SERVER] Removed:", res.deleted_count, "elements")
    return True


def get_wrong_bookings(room_id: ObjectId, check_in: datetime, check_out: datetime, booking_id: ObjectId):
    query = [
        {
            '$match': {
                '_id': {'$exists': 1},
                'is_available': True
            }
        },
        {
            '$project': {
                'bookings': 1
            }
        },
        {
            '$unwind': '$bookings'
        }
    ]
    if room_id is not None:
        query[0]['$match']['_id'] = room_id

    if booking_id is not None:
        query.append({
            "$match": {
                "bookings.booking_id": {'$nin': [ObjectId(booking_id)]}
            }
        })
    query.append({
        '$match': {
            '$or': [
                {
                    '$and': [
                        {
                            'bookings.date_from': {
                                '$gte': check_in
                            }
                        }, {
                            'bookings.date_from': {
                                '$lt': check_out
                            }
                        }
                    ]
                }, {
                    '$and': [
                        {
                            'bookings.date_from': {
                                '$gte': check_in
                            }
                        }, {
                            'bookings.date_to': {
                                '$lte': check_out
                            }
                        }
                    ]
                }, {
                    '$and': [
                        {
                            'bookings.date_from': {
                                '$lte': check_in
                            }
                        }, {
                            'bookings.date_to': {
                                '$gte': check_out
                            }
                        }
                    ]
                }, {
                    '$and': [
                        {
                            'bookings.date_to': {
                                '$gt': check_in
                            }
                        }, {
                            'bookings.date_to': {
                                '$lte': check_out
                            }
                        }
                    ]
                }
            ]
        }
    })

    return list(mongo.rooms.aggregate(query))


def can_be_booked(room_id: ObjectId, check_in: datetime, check_out: datetime, booking_id: ObjectId = None):
    if check_in >= check_out:
        print("[SERVER] Check in date must be less than check out date.")
        return False

    bookings = get_wrong_bookings(room_id, check_in, check_out, booking_id)

    return len(bookings) == 0


def push_bookings(booking_id: ObjectId, customer_id: ObjectId, room_id: ObjectId, check_in: datetime,
                  check_out: datetime):
    booking_in_customers = {
        "booking_id": booking_id,
        "room_id": room_id,
        "date_from": check_in,
        "date_to": check_out
    }
    booking_in_rooms = {
        "booking_id": booking_id,
        "customer_id": customer_id,
        "date_from": check_in,
        "date_to": check_out
    }

    room_update = mongo.rooms.update_one({"_id": room_id}, {"$push": {"bookings": booking_in_rooms}})
    if room_update.matched_count <= 0:
        print("[SERVER] Failed to add booking to a room.")
        return False

    customer_update = mongo.customers.update_one({"_id": customer_id},
                                                 {"$push": {"bookings": booking_in_customers}})
    if customer_update.matched_count <= 0:
        print("[SERVER] Failed to add booking to a customer.")
        return False
    print("[SERVER] Successfully booked a room.")
    return True


def add_new_booking(customer_id: str, room_id: str, check_in: datetime, check_out: datetime):
    try:
        customer_id = ObjectId(customer_id)
        room_id = ObjectId(room_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    if can_be_booked(room_id, check_in, check_out):
        booking_id = ObjectId()
        return push_bookings(booking_id, customer_id, room_id, check_in, check_out)
    else:
        print("[SERVER] Term is colliding.")
        return False


def change_booking(customer_id: str, room_id: str, booking_id: str, check_in: datetime, check_out: datetime):
    try:
        room_id = ObjectId(room_id)
        booking_id = ObjectId(booking_id)
        customer_id = ObjectId(customer_id)
    except Exception as e:
        print("[SERVER]", e)
        return False
    if can_be_booked(room_id, check_in, check_out, booking_id):

        # update in Customers
        customer_update = mongo.customers.update_one(
            {
                "_id": ObjectId(customer_id),
                "bookings.booking_id": booking_id
            },
            {
                "$set": {
                    "bookings.$.date_from": check_in,
                    "bookings.$.date_to": check_out
                }
            }
        )

        if customer_update.matched_count <= 0:
            print("[SERVER] Failed to add booking to a room.")
            return False

        # update Rooms
        room_update = mongo.rooms.update_one(
            {
                "_id": room_id,
                "bookings.booking_id": booking_id
            },
            {
                "$set": {
                    "bookings.$.date_from": check_in,
                    "bookings.$.date_to": check_out
                }
            }
        )

        if room_update.matched_count <= 0:
            print("[SERVER] Failed to add booking to a room.")
            return False
        return True
    else:
        print("[SERVER] You cannot rebook this room.")
        return False


def get_occupied_rooms(check_in: datetime, check_out: datetime):

    booked_rooms = get_wrong_bookings(None, check_in, check_out, None)
    res: set = set()
    for i in booked_rooms:
        res.add(i['_id'])
    return list(res)


def filter_rooms(check_in: datetime = datetime(2400, 1, 1), check_out: datetime = datetime(2400, 1, 2), min_price: float = None, max_price: float = None,
                 room_type: int = None, hotel_city: str = None):

    if check_in is None:
        check_in_fixed = datetime.now().date()
        check_in_fixed = datetime.combine(check_in_fixed, datetime.min.time())
    else:
        check_in_fixed = check_in

    black_list = get_occupied_rooms(check_in_fixed, check_out)

    query = [
        {
            '$match': {
                'is_available': True,
                '_id': {
                    '$nin': black_list
                },
                'price_per_night': {
                    '$gte': 0.0,
                    '$lt': 100000000.0
                },
                'room_type': {'$exists': 1}
            }
        }, {
            '$lookup': {
                'from': 'Hotels',
                'localField': 'hotel_id',
                'foreignField': '_id',
                'as': 'hotel_info'
            }
        }, {
            '$unwind': '$hotel_info'
        }, {
            '$project': {
                '_id': 0,
                'room_id': '$_id',
                'room_type': 1,
                'price_per_night': 1,
                'room_imgUrl': '$imgUrl',
                'hotel_name': '$hotel_info.name',
                'hotel_street': '$hotel_info.street',
                'hotel_city': '$hotel_info.city'
            }
        }, {
            '$match': {
                'hotel_city': {
                    '$exists': 1
                }
            }
        }
    ]

    if min_price is not None:
        query[0]['$match']['price_per_night']['$gte'] = min_price
    if max_price is not None:
        query[0]['$match']['price_per_night']['$lt'] = max_price
    if room_type is not None:
        query[0]['$match']['room_type'] = room_type
    if hotel_city is not None:
        query[4]['$match']['hotel_city'] = hotel_city

    result = mongo.rooms.aggregate(query)
    return list(result)


def get_all_user_bookings(user_id: str):
    try:
        _id = ObjectId(user_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    query = [
        {
            '$match': {
                '_id': _id
            }
        },
        {
            '$unwind': '$bookings'
        },
        {
            '$lookup': {
                'from': 'Rooms',
                'localField': 'bookings.room_id',
                'foreignField': '_id',
                'as': 'room_info'
            }
        },
        {
            '$unwind': '$room_info'
        },
        {
            '$project': {
                '_id': 0,
                'name': 0,
                'surname': 0,
                'email': 0,
                'password': 0,
                'room_info.is_available': 0,
                'room_info.bookings': 0
            }
        },
        {
            '$lookup': {
                'from': 'Hotels',
                'localField': 'room_info.hotel_id',
                'foreignField': '_id',
                'as': 'hotel_info'
            }
        },
        {
            '$unwind': '$hotel_info'
        },
        {
            '$project': {
                'room_id': '$bookings.room_id',
                'booking_id': '$bookings.booking_id',
                'date_from': '$bookings.date_from',
                'date_to': '$bookings.date_to',
                'hotel_id': '$room_info.hotel_id',
                'room_type': '$room_info.room_type',
                'room_number': '$room_info.room_number',
                'price_per_night': '$room_info.price_per_night',
                'room_imgUrl': '$room_info.imgUrl',
                'hotel_name': '$hotel_info.name',
                'hotel_address': '$hotel_info.street',
                'hotel_city': '$hotel_info.city',
                'hotel_zip_code': '$hotel_info.zip_code',
                'hotel_imgUrl': '$hotel_info.imgUrl'
            }
        },
        {
            '$addFields': {
                'can_be_edited': {
                    '$cond': {
                        'if': {
                            '$gt': [
                                '$date_from', datetime.utcnow()
                            ]
                        },
                        'then': True,
                        'else': False
                    }
                }
            }
        }
    ]
    res = list(mongo.customers.aggregate(query))
    for booking in res:
        booking['date_from'] = booking['date_from'].date()
        booking['date_to'] = booking['date_to'].date()
    return res


def remove_booking(booking_id: str, customer_id: str, room_id: str):

    try:
        customer_id = ObjectId(customer_id)
        booking_id = ObjectId(booking_id)
        room_id = ObjectId(room_id)
    except Exception as e:
        print("[SERVER]", e)
        return False

    removed_from_rooms = mongo.rooms.update_one(
        {
            '_id': room_id,
        },
        {
            '$pull': {
                'bookings': {'booking_id': booking_id}
            }
        },
        False,
        True
    )
    if removed_from_rooms.modified_count <= 0:
        print("[SERVER] Error during room update")
        return False

    removed_from_customers = mongo.customers.update_one(
        {
            '_id': customer_id
        },
        {
            '$pull': {
                'bookings': {'booking_id': booking_id}
            }
        },
        False,
        True
    )
    if removed_from_customers.modified_count <= 0:
        print("[SERVER] Error during customer update")
        return False
    return True


def get_all_cities():
    query = [
        {
            '$group': {
                '_id': '$city'
            }
        }, {
            '$project': {
                '_id': 0,
                'city': '$_id'
            }
        }
    ]
    cities = mongo.hotels.aggregate(query)
    return list(cities)


def get_user_email(email: str):
    return mongo.customers.find_one({"email": email})
