"""
Scope: AutomaticSessionFunctionality
"""


from pathlib import Path
from unittest.mock import Mock
import numpy as np
import pytest
from labone.core.helper import LabOneNodePath
from labone.core.shf_vector_data import SHFDemodSample
from labone.core.value import AnnotatedValue, Value
from labone.mock import AutomaticSessionFunctionality
from labone.mock.automatic_session_functionality import PathData
from labone.mock.mock_server import MockServer
from labone.mock.session_mock_template import SessionMockTemplate


async def get_functionality_with_state(state: dict[LabOneNodePath, Value]):
    functionality = AutomaticSessionFunctionality({path: {} for path in state.keys()})
    for path, value in state.items():
        await functionality.set(AnnotatedValue(value=value, path=path))
    return functionality


async def check_state_agrees_with(
    functionality: AutomaticSessionFunctionality,
    state: dict[LabOneNodePath, Value],
) -> bool:
    for path, value in state.items():
        if (await functionality.get(path)).value != value:
            return False
    return True


@pytest.mark.asyncio
async def test_remembers_state():
    functionality = AutomaticSessionFunctionality({"/a/b": {}})
    await functionality.set(AnnotatedValue(value=123, path="/a/b"))
    assert (await functionality.get("/a/b")).value == 123


@pytest.mark.asyncio
async def test_state_overwritable():
    functionality = AutomaticSessionFunctionality({"/a/b": {}})
    await functionality.set(AnnotatedValue(value=123, path="/a/b"))
    await functionality.set(AnnotatedValue(value=456, path="/a/b"))
    assert (await functionality.get("/a/b")).value == 456


@pytest.mark.asyncio
async def test_seperate_state_per_path():
    functionality = AutomaticSessionFunctionality({"/a/b": {}, "/a/c": {}})
    await functionality.set(AnnotatedValue(value=123, path="/a/b"))
    await functionality.set(AnnotatedValue(value=456, path="/a/c"))
    assert (await functionality.get("/a/b")).value == 123
    assert (await functionality.get("/a/c")).value == 456


@pytest.mark.asyncio
async def test_cannot_get_outside_of_tree_structure():
    functionality = AutomaticSessionFunctionality({"/a/b": {}})
    with pytest.raises(Exception):
        await functionality.get("/a/c")


@pytest.mark.asyncio
async def test_cannot_set_outside_of_tree_structure():
    functionality = AutomaticSessionFunctionality({"/a/b": {}})
    with pytest.raises(Exception):
        await functionality.set(AnnotatedValue(value=123, path="/a/c"))


@pytest.mark.asyncio
async def test_list_nodes_answered_by_tree_structure():
    functionality = AutomaticSessionFunctionality(
        {"/x": {}, "/x/y": {}, "/v/w/q/a": {}}
    )
    assert set(await functionality.list_nodes("*")) == {"/x", "/x/y", "/v/w/q/a"}


@pytest.mark.parametrize(
    ("path_to_info", "path", "expected"),
    [
        # test option to get all paths with *
        ({}, "*", {}),
        ({"/a/b": {}}, "*", {"/a/b": {}}),
        ({"/a": {}, "/b": {}, "/c/d/e": {}}, "*", {"/a": {}, "/b": {}, "/c/d/e": {}}),
        # if specific path, not necessarily all paths are returned
        ({}, "/a", {}),
        ({"/a/b": {}}, "/c", {}),
        (
            {"/x/y": {}, "/x/z/n": {"Description": "_"}, "/x/z/q/a": {}},
            "/x/z",
            {"/x/z/n": {"Description": "_"}, "/x/z/q/a": {}},
        ),
        ({"/a/b": {}, "/a/c": {}}, "/a", {"/a/b": {}, "/a/c": {}}),
        # a path matches itself
        ({"/a/b": {}}, "/a/b", {"/a/b": {}}),
        # a path does not match itself plus wildcard
        ({"/a/b": {}}, "/a/b/*", {}),
        # test wildcard constillations
        ({"/a/b": {}, "/a/c": {}}, "/*/b", {"/a/b": {}}),
        ({"/a/b": {}, "/a/c": {}}, "/*", {"/a/b": {}, "/a/c": {}}),
    ],
)
@pytest.mark.asyncio
async def test_list_nodes_info(path_to_info, path, expected):
    functionality = AutomaticSessionFunctionality(path_to_info)
    assert await functionality.list_nodes_info(path) == expected


@pytest.mark.parametrize(
    "path_to_info",
    [
        {},
        {"/a/b": {}},
        {"/a": {}, "/b": {}, "/c/d/e": {}},
        {"/x/y/1": {}, "/x/y/2": {}, "/x/z/n": {}, "/x/z/q/a": {}},
    ],
)
@pytest.mark.parametrize(
    "path",
    [
        "",
        "/a/*",
        "/x/y/*",
        "/x/z/*",
        "/x/*",
        "/*",
    ],
)
@pytest.mark.asyncio
async def test_consistency_list_nodes_vs_list_nodes_info(path_to_info, path):
    functionality = AutomaticSessionFunctionality(path_to_info)

    assert set((await functionality.list_nodes_info(path)).keys()) == set(
        await functionality.list_nodes(path)
    )


# @pytest.mark.parametrize(
#     ("nodes", "path", "expected"),
#     [
#         ([], "", []),
#         (["/a/b"], "", ["/a/b"]),
#         (["/a/b"], "/*", ["/a/b"]),
#         (["/a/b"], "/a/*", ["/a/b"]),
#         (["/a/b"], "/*/*", ["/a/b"]),
#         (["/a/b/c","/a/b/d"], "/a/b/*", ["/a/b/c","/a/b/d"]),
#         (["/a/b/c","/a/b/d"], "/a", ["/a/b/c","/a/b/d"]),
#         (["/a/b/c","/a/b/d"], "/a/b/c", ["/a/b/c"]),
#         (["/a/b/c","/a/b","/b/b/d"], "/a", ["/a/b/c","/a/b"]),
#         ]
#     )
# def test_resolve_wildcards_labone(nodes, path, expected):
#     assert resolve_wildcards_labone(path, nodes) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("/*", {1, 2, 3, 4, 5}),
        ("*", {1, 2, 3, 4, 5}),
        ("/a/b/c", {1}),
        ("/a/b", {1, 2}),
        ("/a", {1, 2, 3, 4}),
        ("/a/x", {3, 4}),
    ],
)
@pytest.mark.asyncio
async def test_get_with_expression(expression, expected):
    functionality = await get_functionality_with_state(
        {
            "/a/b/c": 1,
            "/a/b/d": 2,
            "/a/x": 3,
            "/a/x/y": 4,
            "/b": 5,
        }
    )
    assert {
        ann.value for ann in (await functionality.get_with_expression(expression))
    } == expected


@pytest.mark.parametrize(
    ("expression", "value", "expected_new_state"),
    [
        ("*", 7, {"/a/b/c": 7, "/a/b/d": 7, "/a/x": 7, "/a/x/y": 7, "/b": 7}),
        ("/a/b/c", 7, {"/a/b/c": 7, "/a/b/d": 2, "/a/x": 3, "/a/x/y": 4, "/b": 5}),
        ("/a/b", 7, {"/a/b/c": 7, "/a/b/d": 7, "/a/x": 3, "/a/x/y": 4, "/b": 5}),
        (
            "/a",
            7,
            {
                "/a/b/c": 7,
                "/a/b/d": 7,
                "/a/x": 7,
                "/a/x/y": 7,
                "/b": 5,
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_set_with_expression(expression, value, expected_new_state):
    functionality = await get_functionality_with_state(
        {
            "/a/b/c": 1,
            "/a/b/d": 2,
            "/a/x": 3,
            "/a/x/y": 4,
            "/b": 5,
        }
    )

    await functionality.set_with_expression(
        AnnotatedValue(value=value, path=expression)
    )

    # assert {ann.value for ann in (await functionality.get_with_expression(expression))} == expected
    assert await check_state_agrees_with(functionality, expected_new_state)


# @pytest.mark.asyncio
# async def test_prevent_server_from_being_started_twice():
#     functionality = AutomaticSessionFunctionality({"/a/b": {}})
#     mock_server = MockServer(
#         capability_bytes=Path(__file__).parent.parent / "resources" / "session.bin",
#         concrete_server=SessionMockTemplate(functionality),
#     )
#     client_connection = await mock_server.start()
#     with pytest.raises(Exception):
#         await mock_server.start_server()


# complex,
# np.ndarray,
# SHFDemodSample,
# TriggerSample,
# CntSample,
# None,


@pytest.mark.parametrize(
    ("value", "equals_function"),
    [
        (5, lambda a, b: a == b),
        (6.3, lambda a, b: a == b),
        ("hello", lambda a, b: a == b),
        (b"hello", lambda a, b: a == b),
        (2 + 3j, lambda a, b: a == b),
        (np.array([1, 2, 3]), lambda a, b: np.all(a == b)),
    ],
)
@pytest.mark.asyncio
async def test_handling_of_multiple_data_types(value: Value, equals_function):
    functionality = AutomaticSessionFunctionality({"/a/b": {}})
    await functionality.set(AnnotatedValue(value=value, path="/a/b"))
    assert equals_function((await functionality.get("/a/b")).value, value)
