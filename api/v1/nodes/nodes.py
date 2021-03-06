#!/usr/bin/python3
"""
Index route for nodes api
"""

from api.v1.nodes import app_nodes
from models import storage
from flask import jsonify, Response, request, render_template
from models.custom import CustomNode
from models.board import Board
from models.logger import Logger
from models.user import User
import traceback
import json
import os
import sys
from threading import Thread
import threading


@app_nodes.route('/nodes/<node_id>',
                 methods=['GET'],
                 strict_slashes=False)
def nodes(node_id):
    """
    Returns list of nodes by user_id
    """
    node = storage.get(CustomNode, node_id)
    resp = node.to_dict()
    # resp = json.dumps(resp)
    return Response(resp, mimetype='application/json')


@app_nodes.route('/nodes/<node_id>/savecolor',
                 methods=['POST'], strict_slashes=False)
def nodes_savecolor(node_id):
    """
    Returns list of nodes by user_id
    """
    node = storage.get(CustomNode, node_id)
    node.color = request.get_json()['color']
    node.save()
    return Response(json.dumps({'status': 'saved'}),
                    mimetype='application/json', status=200)


@app_nodes.route('/nodes/<node_id>/save_analisis_params',
                 methods=['POST'], strict_slashes=False)
def save_analisis_data(node_id):
    """
    Saves the incoming object analisis data attribute of node_id to db
    """
    an_data = []
    try:
        an_data = request.get_json()['params']
    except Exception as e:
        print(e)
    node = storage.get(CustomNode, node_id)
    if node:
        node.analisis_params = json.dumps(an_data)


def run_thread(node_id):
    """
    Run threaded node
    """
    print('Start Threaded process')
    try:
        node = storage.get(CustomNode, node_id)
        logger = Logger(node.user_id)
        test_file = {
            'status': 'started',
            'node_id': node_id,
            'messages': ['Starting flow']
        }
        with open('./api/running/{}.test'.format(node_id), 'w') as test:
            test.write(json.dumps(test_file))
        resp = node.run_node_task(({}, {}), logger, node_id)
        logger_content = str(logger)
        with open('./api/running/{}.test'.format(node_id), 'r') as test:
            test_file = json.loads(test.read())
        test_file['logger'] = dict(logger.json())
        test_file['status'] = 'completed'
        test_file['node_id'] = node_id
        with open('./api/running/{}.test'.format(node_id), 'w') as test:
            test.write(json.dumps(test_file))
        logger.reset()
        print('Finishing thread')
        # thre = threading.currentThread()
        storage.close()
        # threading.Event().set()
        # Thread.join(thre, None)
    except Exception as e:
        print('Thread Fail:\n\t', e)
        traceback.print_exc()
        # threading.currentThread().join()
    # dict(logger.json())


@app_nodes.route('/nodes/<node_id>/run',
                 methods=['GET'], strict_slashes=False)
def run_node(node_id):
    """
    run the node proccesses and conections
    """
    Thread(target=run_thread, args=(node_id, )).start()

    return Response(json.dumps({'status': 'started'}),
                    mimetype='application/json',
                    status=200)


@app_nodes.route('/nodes/<node_id>/add_connection',
                 methods=['POST'], strict_slashes=False)
def add_connection(node_id):
    """
    Add a connection to the given id
    """
    node = storage.get(CustomNode, node_id)
    new_connection = request.get_json()['con_id']
    typ = request.get_json()['type']
    if typ == 'out':
        outnodes = json.loads(node.outnodes)
        if new_connection not in outnodes:
            outnodes.append(new_connection)
        node.outnodes = json.dumps(outnodes)
    else:
        innodes = json.loads(node.innodes)
        if new_connection not in innodes:
            innodes.append(new_connection)
        node.innodes = json.dumps(innodes)
    node.save()
    return Response({'success': 'OK'}, status=200)


@app_nodes.route('/nodes/<node_id>/del_connection',
                 methods=['DELETE'], strict_slashes=False)
def del_connection(node_id):
    """
    Delete the out
    """
    typ = request.get_json()['type']
    conn = request.get_json()['con_id']
    node = storage.get(CustomNode, node_id)
    # print(typ, conn, node.id)
    if typ == 'out':
        # print('')
        outnodes = json.loads(node.outnodes)
        if conn in outnodes:
            # print('remove', conn)
            del outnodes[outnodes.index(conn)]
        node.outnodes = json.dumps(outnodes)
    if typ == 'in':
        # print('')
        innodes = json.loads(node.innodes)
        if conn in innodes:
            # print('remove', conn)
            del innodes[innodes.index(conn)]
        node.innodes = json.dumps(innodes)
    node.save()
    return Response({'state': 'Connection removed'}, status=200)


def load_templates():
    """
    load templates from .dim template file
    """
    with open('./api/node_templates/templates.dim', 'r') as templates:
        temps = json.loads(templates.read())
        return temps


def copy_node(board, node, data=None, complete=False):
    """
    Copy a node
    """
    new_node = CustomNode()
    in_node = node
    # print(in_node)
    del in_node['id']
    sample_keys = in_node.keys()
    for key in sample_keys:
        val = in_node[key]
        if type(val) == dict or type(val) == list:
            val = json.dumps(val)
        setattr(new_node, key, val)
    if complete:
        new_node.innodes = json.dumps(node['innodes'])
        new_node.outnodes = json.dumps(node['outnodes'])
    else:
        new_node.innodes = json.dumps([])
        new_node.outnodes = json.dumps([])
    if data:
        new_node.data = json.dumps(data)
    new_node.analisis_mode = node['analisis_mode']
    new_node.board_id = board.id
    new_node.user_id = board.user_id
    new_node.save()
    nodes = json.loads(board.nodes)
    nodes[new_node.id] = {'x': 20, 'y': 50}
    board.nodes = json.dumps(nodes)
    board.save()
    return new_node


@app_nodes.route('/boards/<board_id>/create_node', methods=['POST'],
                 strict_slashes=False)
def creates_new_node(board_id):
    """
    Creates a new node an likit to board id and user id
    """
    typo = request.get_json()['type']
    board = storage.get(Board, board_id)
    user_id = board.user_id
    # print(user_id)
    nodes = load_templates()
    if typo in nodes['nodes'].keys():
        js = request.get_json()
        if 'data' in js.keys():
            n_node = copy_node(board, nodes['nodes'][typo], js['data'])
        else:
            n_node = copy_node(board, nodes['nodes'][typo])
        return Response(
            json.dumps(json.loads(n_node.to_dict())),
            mimetype='application/json', status=200)
    new_node = CustomNode()
    new_node.name = 'New'
    new_node.user_id = user_id
    new_node.board_id = board_id
    if 'whatsapp' in typo:
        new_node.work_type = 'sender'
        new_node.name = typo
    new_node.save()
    nodes = json.loads(board.nodes)
    nodes[new_node.id] = {'x': 20, 'y': 60}
    board.nodes = json.dumps(nodes)
    board.save()
    # template = render_template('node.html',
    # nodes=[json.loads(new_node.to_dict())], )
    return Response(json.dumps(json.loads(new_node.to_dict())),
                    mimetype='application/json', status=200)


@app_nodes.route('/nodes/<node_id>', methods=['DELETE'], strict_slashes=False)
def delete_node(node_id):
    """
    Delete a node instance, recursively
    and all references in any node at the board
    """
    try:
        node = storage.get(CustomNode, node_id)
        board = storage.get(Board, node.board_id)
        nodes = json.loads(board.nodes)
        for n_id in nodes:
            nod = storage.get(CustomNode, n_id)
            nod_inns = json.loads(nod.innodes)
            if node.id in nod_inns:
                del nod_inns[nod_inns.index(node.id)]
            nod_outs = json.loads(nod.outnodes)
            if node.id in nod_outs:
                del nod_outs[nod_outs.index(node.id)]
            nod.innodes = json.dumps(nod_inns)
            nod.outnodes = json.dumps(nod_outs)
            nod.save()
        if node_id in nodes:
            del nodes[node_id]
        board.nodes = json.dumps(nodes)
        board.save()
        storage.delete(node)
        return Response('deleted', status=200)
    except Exception as e:
        return Response(str(e), status=500)


@app_nodes.route('/nodes/<node_id>/save', methods=['POST'],
                 strict_slashes=False)
def save_entire_node(node_id):
    """
    saves the entire node object
    """
    in_node = request.get_json()
    node = storage.get(CustomNode, node_id)
    sample_keys = json.loads(node.to_dict()).keys()
    # print(in_node)
    if 'type' not in in_node:
        node.type = 'custom'
    for key in sample_keys:
        if key == 'analisis_mode':
            if key not in in_node:
                setattr(node, key, '')
        if key not in in_node:
            # print('excluding', key)
            continue
        val = in_node[key]
        if type(val) == dict or type(val) == list:
            val = json.dumps(val)
        setattr(node, key, val)
    print('Saved node\n', node.to_dict())
    node.save()
    return Response(json.dumps({'id': node_id}), status=200,
                    mimetype='application/json')


@app_nodes.route('/users/<board_id>/boards_nodes', methods=['GET'],
                 strict_slashes=False)
def get_boards_nodes(board_id):
    """
    return a list ob boards an their node ids
    """
    board = storage.get(Board, board_id)
    user = storage.get(User, board.user_id)
    boards = storage.all(Board)
    bs = {}
    for b in boards.values():
        # print(b)
        if b.user_id == user.id:
            bs[b.id] = {}
            bs[b.id]['nodes'] = []
            # print(b.nodes)
            for node in json.loads(b.nodes).keys():
                print(node)
                n = storage.get(CustomNode, node)
                if n is not None:
                    bs[b.id]['nodes'].append({'name': n.name, 'id': n.id})
            bs[b.id]['name'] = b.name
    # print(bs)
    return Response(json.dumps(bs), mimetype='application/json', status=200)


@app_nodes.route('/nodes/<node_id>/copy_to/<board_id>', methods=['GET'],
                 strict_slashes=False)
def copy_node_to_board(node_id, board_id):
    """
    create a new node based on an existin one from other board
    """
    node = storage.get(CustomNode, node_id)
    new_node = CustomNode()
    in_node = json.loads(node.to_dict())
    sample_keys = json.loads(node.to_dict()).keys()
    # print(in_node)
    del in_node['id']
    for key in sample_keys:
        if key in in_node:
            val = in_node[key]
            if type(val) == dict or type(val) == list:
                val = json.dumps(val)
            setattr(new_node, key, val)
    new_node.innodes = json.dumps([])
    new_node.outnodes = json.dumps([])
    new_node.board_id = board_id
    new_node.save()
    board = storage.get(Board, board_id)
    nodes = json.loads(board.nodes)
    nodes[new_node.id] = {'x': 20, 'y': 50}
    board.nodes = json.dumps(nodes)
    board.save()
    return Response('success', status=200)
