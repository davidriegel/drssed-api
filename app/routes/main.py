from flask import Blueprint

api = Blueprint("main", __name__)

@api.route('/ping', methods=['GET'])
def ping_reachablility():
    return {}, 200