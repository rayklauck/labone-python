from unittest.mock import patch, Mock

import pytest

from labone.core import AnnotatedValue
from labone.nodetree.errors import LabOneInvalidPathError, \
    LabOneInappropriateNodeTypeError
from labone.nodetree.helper import split_path, join_path
from labone.nodetree.node import NodeTreeManager, ResultNode
from tests.nodetree.conftest import MockResultNode, MockMetaNode


class TestMetaNode:
    @pytest.mark.parametrize(('subtree_structure'), [({'a':[],'b':[],'c':[]}), {}, {'a':[]}, {'b':[],'a':[]}])
    def test_iter(self, subtree_structure, result_node):
        result_node._subtree_paths = subtree_structure

        sub_list = sorted(list(subtree_structure.keys()))

        with patch("labone.nodetree.node.ResultNode.__getitem__",
                   return_value='subnode') as patch_getitem:

            for i, subnode in enumerate(result_node):
                patch_getitem.assert_called_with(sub_list[i])
                assert subnode == 'subnode'

    @pytest.mark.parametrize(('subtree_structure'),
                             [({'a': [], 'b': [], 'c': []}), {}, {'a': []},
                              {'b': [], 'a': []}])
    def test_len(self, subtree_structure, result_node):
        result_node._subtree_paths = subtree_structure

        assert len(result_node) == len(subtree_structure)

    @pytest.mark.parametrize(('path_aliases','start_path','expected'),
                             [({'a':'b'},'a','b'),
                              ({},'a','a'),
                              ({'a':'b', 'b':'c'},'a','c'),
                              ({'a': 'b', 'b': 'c'}, 'b', 'c'),
                              ({'a': 'b', 'b': 'c'}, 'x', 'x'),
                                ({'a/b': 'c/d', 'c/d': 'e/f'}, 'a/b', 'e/f')])
    def test_redirect(self, path_aliases, start_path, expected, zi):
        zi._path_aliases = path_aliases
        assert zi._redirect(start_path) == expected

    @pytest.mark.parametrize(('start_path_segments','subtree_structure','test_path_segments', 'expected'),
        [
            ((), [], (), False),
            (('a',),[], ('a',), False),
            ((), ['a'], ('a',), True),
            (('a','b'), [], ('a','b'), False),
            (('a',), ['c'], ('a', 'c'), True),
            (('a', 'b'), ['c'], ('a', 'b', 'c'), True),
            (('a', 'b'), ['c'], ('a', 'b', 'd'), False),
            (('a', 'b','c','d'), ['d'], ('a', 'b','c', 'd','d'), True),
            (('a',), ['c'], ('a', 'c', 'd'), False),
            (('a',), ['c'], ('a', 'c', 'd','e','f','g'), False),

        ])
    @pytest.mark.parametrize('as_node', [True, False])
    def test_is_child_node(self, as_node, start_path_segments, subtree_structure, test_path_segments, expected):
        node = MockMetaNode(start_path_segments)
        node._subtree_paths = subtree_structure

        if as_node:
            sub = MockMetaNode(test_path_segments)
        else:
            sub = test_path_segments
        assert node.is_child_node(sub) == expected


class TestResultNode():
    def test_init(self):
        node = ResultNode(
            tree_manager='tree_manager',
            path_segments='path_segments',
            subtree_paths='subtree_paths',
            path_aliases='path_aliases',
            value_structure='value_structure',
            timestamp='timestamp',
        )
        assert node._tree_manager == 'tree_manager'
        assert node._path_segments == 'path_segments'
        assert node._subtree_paths == 'subtree_paths'
        assert node._path_aliases == 'path_aliases'
        assert node._value_structure == 'value_structure'
        assert node._timestamp == 'timestamp'

    def test_getattr(self, result_node):
        with patch("labone.nodetree.node.normalize_path_segment",
                   side_effect=lambda x:x) as patch_normalize:
            with patch.object(ResultNode, "try_generate_subnode",
                              return_value='subnode'):
                subnode = result_node.__getattr__("next")

                patch_normalize.assert_called_once_with("next")
                ResultNode.try_generate_subnode.assert_called_once_with("next")
                assert subnode == 'subnode'


    @pytest.mark.parametrize(
        'path_segments',
        [
            (),
            ('next',),
            ('next', 'next2', 'next3'),
        ]
    )
    def test_getitem(self, path_segments, result_node):
        path = join_path(path_segments)

        subnode_mock = Mock()
        stubs = [MockResultNode(path_segments[:i+1])
                            for i in range(len(path_segments))]
        subnode_mock.side_effect = stubs

        with patch('labone.nodetree.node.normalize_path_segment',
                   side_effect=lambda x:x) as normalize_patch:
            with patch('labone.nodetree.node.ResultNode.try_generate_subnode', subnode_mock) as try_generate_patch:

                subnode = MockResultNode(()).__getitem__(path)

                assert subnode.path == path

                for i in range(len(path_segments)):
                    normalize_patch.assert_any_call(path_segments[i])
                    try_generate_patch.assert_any_call(path_segments[i])

    def test_getitem_too_long(self):
        segments = ('next', 'next2')

        subnode_mock = Mock()
        subnode_mock.side_effect = [AnnotatedValue(path='next', value=1)]

        with patch('labone.nodetree.node.normalize_path_segment',
                   side_effect=lambda x:x) as normalize_patch:
            with patch('labone.nodetree.node.ResultNode.try_generate_subnode',
                       subnode_mock) as try_generate_patch:
                with pytest.raises(LabOneInvalidPathError):
                    MockResultNode(()).__getitem__(join_path(segments))

                normalize_patch.assert_called_once_with('next')
                try_generate_patch.assert_called_once_with('next')





    @pytest.mark.parametrize('keys',
                             [{'a',},
                              {'a', 'b', 'c', 'd'}
                              ])
    def test_dir(self, keys):
        result_node = MockResultNode(())
        result_node._subtree_paths = {k: [] for k in keys}

        with patch('labone.nodetree.node.pythonify_path_segment', side_effect=lambda x:x) as pythonify_mock:
            assert keys <= set(result_node.__dir__())
            for k in keys:
                pythonify_mock.assert_any_call(k)

    @pytest.mark.parametrize(('next_segment', 'subtree_paths','expected'),
                             [('a', set(), False),
                              ('a', {'a', 'b'}, True),
                              ('0', {'0'}, True),
                              ('c', {'a','c','e','f'}, True),
                              ('d', {'a', 'c', 'e', 'f'}, False)
                              ])
    def test_contains_plain_value(self, next_segment, subtree_paths, expected):
        node = MockResultNode(())
        node._subtree_paths = subtree_paths

        with patch('labone.nodetree.node.normalize_path_segment',
                   side_effect=lambda x: x) as normal_patch:
            decision = node.__contains__(next_segment)
            normal_patch.assert_called_once_with(next_segment)
            assert decision == expected

    @pytest.mark.parametrize(('next_segment'),
                             ['a',
                              'b',
                              ])
    def test_contains_node(self, next_segment):
        arg = MockResultNode((next_segment,))

        with patch('labone.nodetree.node.ResultNode.is_child_node') as child_patch:
            MockResultNode(()).__contains__(arg)
            child_patch.assert_called_once_with(arg)

    @pytest.mark.parametrize(('next_segment'),
                             ['a',
                              'b',
                              ])
    def test_contains_annotated_value(self, next_segment):
        path = join_path(next_segment)

        with patch('labone.nodetree.node.ResultNode.is_child_node') as child_patch:
            with patch('labone.nodetree.node.split_path',
                       return_value=next_segment) as split_patch:
                MockResultNode(()).__contains__(AnnotatedValue(path=path, value=0))
                split_patch.assert_called_once_with(path)
                child_patch.assert_called_once_with(next_segment)

    def test_call(self):
        with pytest.raises(LabOneInappropriateNodeTypeError):
            MockResultNode(()).__call__()

    def test_str(self, result_node):
        assert isinstance(str(result_node), str)

    def test_repr(self, result_node):
        assert isinstance(repr(result_node), str)

    @pytest.mark.parametrize(('path', 'expected'),
                             [('/a', {1,2,3,4,5}),
                              ('/b', set()),
                              ('/a/b', {2,3,4,5}),
                              ('/a/b/d', {4,5}),
                              ('/a/b/d/e', {5}),
                              ('/a/b/c', {3}),
                              ('/a/b/e', set())
                              ])
    def test_results(self, path, expected):
        value_structure = {'/a': 1, '/a/b': 2, '/a/b/c': 3, '/a/b/d': 4, '/a/b/d/e':5}
        node = MockResultNode(tuple(split_path(path)))
        node._value_structure = value_structure

        assert set(node.results()) == expected


    def test_try_generate_subnode(self, result_node, monkeypatch):
        segments = ('zi', 'next')
        with patch("labone.nodetree.node.MetaNode._redirect",
                   side_effect=lambda x: x) as patch_redirect:
            with patch("labone.nodetree.node.ResultNode.__init__",
                       return_value=None) as patch_init:
                with patch.object(NodeTreeManager, "find_substructure",
                                  return_value={"level": []}) as patch_find_structure:
                    deeper = result_node.try_generate_subnode(next_path_segment="next")

                    patch_redirect.assert_called_once_with(segments)
                    patch_find_structure.assert_called_once_with(segments)
                    patch_init.assert_called_once_with(
                        tree_manager=result_node.tree_manager,
                        path_segments=(*result_node.path_segments, "next"),
                        subtree_paths={"level": []},
                        value_structure=result_node._value_structure,
                        timestamp=result_node._timestamp,
                        path_aliases=result_node.path_aliases,
                    )
                    assert isinstance(deeper, ResultNode)

    def test_try_generate_subnode_leaf(self, result_node, monkeypatch):
        segments = ('zi', 'next')
        path = '/zi/next'
        value = AnnotatedValue(path=path, value=1)

        def fake_init_func(self, *_, **__):
            self._path_segments = segments

        with patch("labone.nodetree.node.MetaNode._redirect",
                   return_value=segments) as patch_redirect:
            with patch.object(NodeTreeManager, "find_substructure",
                              return_value={}) as patch_find_structure:
                with patch.dict(result_node._value_structure, {path: value}):
                    with patch.object(ResultNode, "__init__",
                                      fake_init_func) as patch_init:
                        deeper = result_node.try_generate_subnode(
                            next_path_segment="next")

                        patch_redirect.assert_called_once_with(segments)
                        patch_find_structure.assert_called_once_with(segments)
                        assert deeper == value

    def test_try_generate_subnode_invalid(self, result_node, monkeypatch):
        segments = ('zi', 'next')
        with patch("labone.nodetree.node.MetaNode._redirect",
                   side_effect=lambda x:x) as patch_redirect:
            with patch.object(NodeTreeManager, "find_substructure",
                              side_effect=LabOneInvalidPathError()) as patch_find_structure:
                with pytest.raises(LabOneInvalidPathError):
                    result_node.try_generate_subnode(next_path_segment="next")

                patch_redirect.assert_called_once_with(segments)
                patch_find_structure.assert_called_once_with(segments)