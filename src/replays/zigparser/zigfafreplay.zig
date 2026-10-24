const std = @import("std");

const py = @import("py");
const converter = @import("converter.zig");
const decompressor = @import("decompressor.zig");
const parser = @import("parser.zig");
const structs = @import("structs.zig");

var threaded: std.Io.Threaded = .init_single_threaded;
const io = threaded.io();

fn parse_replaydata(_: [*c]py.PyObject, args: [*c]py.PyObject) callconv(.c) [*c]py.PyObject {
    @setRuntimeSafety(true);
    var buf: py.Py_buffer = undefined;
    if (py.PyArg_ParseTuple(args, "y*", &buf) == 0) {
        return null;
    }
    defer py.PyBuffer_Release(&buf);

    const allocator = std.heap.c_allocator;

    const size: usize = @intCast(buf.len);
    const body: []u8 = @as([*]u8, @ptrCast(buf.buf))[0..size];
    var replay_parser = parser.parse(body, allocator) catch |err| {
        switch (err) {
            error.Desync => {
                py.PyErr_SetString(py.PyExc_RuntimeError, "Replay is desynced");
                return null;
            },
            else => {
                return py.Py_BuildValue("");
            },
        }
    };
    defer replay_parser.deinit(allocator);
    return converter.convert_replaydata(replay_parser);
}

fn parse_compressed(_: [*c]py.PyObject, args: [*c]py.PyObject) callconv(.c) [*c]py.PyObject {
    @setRuntimeSafety(true);
    var buf: py.Py_buffer = undefined;
    if (py.PyArg_ParseTuple(args, "y*", &buf) == 0) {
        return null;
    }
    defer py.PyBuffer_Release(&buf);

    const allocator = std.heap.c_allocator;

    const size: usize = @intCast(buf.len);
    const compressed: []u8 = @as([*]u8, @ptrCast(buf.buf))[0..size];

    const preprocessed = decompressor.decompress(compressed, allocator) catch return py.Py_BuildValue("");
    defer preprocessed.deinit(allocator);

    var replay_parser = parser.parse(preprocessed.data, allocator) catch |err| {
        switch (err) {
            error.Desync => {
                py.PyErr_SetString(py.PyExc_RuntimeError, "Replay is desynced");
                return null;
            },
            else => {
                return py.Py_BuildValue("");
            },
        }
    };
    defer replay_parser.deinit(allocator);
    return converter.convert_full(replay_parser, preprocessed.metadata.value);
}

fn parse_file(_: [*c]py.PyObject, args: [*c]py.PyObject) callconv(.c) [*c]py.PyObject {
    @setRuntimeSafety(true);
    var buf: py.Py_buffer = undefined;
    if (py.PyArg_ParseTuple(args, "s*", &buf) == 0) {
        return null;
    }
    defer py.PyBuffer_Release(&buf);

    const allocator = std.heap.c_allocator;

    const size: usize = @intCast(buf.len);
    const path: []u8 = @as([*]u8, @ptrCast(buf.buf))[0..size];

    const preprocessed = decompressor.decompress_file(io, path, allocator) catch return py.Py_BuildValue("");
    defer preprocessed.deinit(allocator);

    var replay_parser = parser.parse(preprocessed.data, allocator) catch |err| {
        switch (err) {
            error.Desync => {
                py.PyErr_SetString(py.PyExc_RuntimeError, "Replay is desynced");
                return null;
            },
            else => {
                return py.Py_BuildValue("");
            },
        }
    };
    defer replay_parser.deinit(allocator);
    return converter.convert_full(replay_parser, preprocessed.metadata.value);
}

fn chart_rolling_window(_: [*c]py.PyObject, args: [*c]py.PyObject) callconv(.c) [*c]py.PyObject {
    @setRuntimeSafety(true);
    var chart_data: *py.PyObject = undefined;
    var ticks: c_long = undefined;
    if (py.PyArg_ParseTuple(args, "Ol", &chart_data, &ticks) == 0) {
        return null;
    }
    const allocator = std.heap.c_allocator;

    const items = py.PyDict_Items(chart_data);
    defer py.Py_DecRef(items);

    const num_items: usize = @intCast(py.PyList_Size(items));
    const u_ticks: usize = @intCast(ticks);

    var max_cpm: u32 = 0;

    const rolling_dict = py.PyDict_New();
    for (0..num_items) |i| {
        var cpm: u32 = 0;
        const pair = py.PyList_GetItem(items, @as(isize, @intCast(i)));
        const player_id = py.PyTuple_GetItem(pair, 0);
        const ticklist = py.PyTuple_GetItem(pair, 1);
        const ticklist_size: usize = @intCast(py.PyList_Size(ticklist));
        var actions_at_tick = std.ArrayList(u32).initCapacity(allocator, u_ticks + 600) catch {
            py.Py_DecRef(rolling_dict);
            return py.Py_BuildValue("");
        };
        defer actions_at_tick.deinit(allocator);

        for (0..u_ticks + 600) |_| {
            actions_at_tick.append(allocator, 0) catch {
                py.Py_DecRef(rolling_dict);
                return py.Py_BuildValue("");
            };
        }

        for (0..ticklist_size) |index| {
            const action_tick = py.PyLong_AsSize_t(
                py.PyList_GetItem(
                    ticklist,
                    @as(isize, @intCast(index)),
                ),
            );
            actions_at_tick.items[action_tick] += 1;
            if (action_tick < 600) cpm += 1;
        }

        const rolling_list = py.PyList_New(ticks);
        _ = py.PyList_SetItem(rolling_list, 0, py.Py_BuildValue("i", cpm));
        for (1..u_ticks) |index| {
            cpm = cpm + actions_at_tick.items[index + 599] - actions_at_tick.items[index - 1];

            if (cpm > max_cpm) max_cpm = cpm;

            _ = py.PyList_SetItem(
                rolling_list,
                @as(isize, @intCast(index)),
                py.Py_BuildValue("i", cpm),
            );
        }
        _ = py.PyDict_SetItem(rolling_dict, player_id, rolling_list);
        py.Py_DecRef(rolling_list);
    }
    const ret = py.PyDict_New();
    const py_max_cpm = py.Py_BuildValue("i", max_cpm);
    _ = py.PyDict_SetItemString(ret, "max_cpm", py_max_cpm);
    _ = py.PyDict_SetItemString(ret, "cpm_data", rolling_dict);
    py.Py_DecRef(py_max_cpm);
    py.Py_DecRef(rolling_dict);
    return ret;
}

var Methods = [_]py.PyMethodDef{
    py.PyMethodDef{
        .ml_name = "parse_file",
        .ml_meth = parse_file,
        .ml_flags = py.METH_VARARGS,
        .ml_doc = null,
    },
    py.PyMethodDef{
        .ml_name = "parse_compressed",
        .ml_meth = parse_compressed,
        .ml_flags = py.METH_VARARGS,
        .ml_doc = null,
    },
    py.PyMethodDef{
        .ml_name = "parse_replaydata",
        .ml_meth = parse_replaydata,
        .ml_flags = py.METH_VARARGS,
        .ml_doc = null,
    },
    py.PyMethodDef{
        .ml_name = "chart_rolling_window",
        .ml_meth = chart_rolling_window,
        .ml_flags = py.METH_VARARGS,
        .ml_doc = null,
    },
    py.PyMethodDef{
        .ml_name = null,
        .ml_meth = null,
        .ml_flags = 0,
        .ml_doc = null,
    },
};

var module = py.PyModuleDef{
    .m_base = py.PyModuleDef_Base{
        .ob_base = .{
            .unnamed_0 = .{ .ob_refcnt_full = 1 },
            .ob_type = null,
        },
        .m_init = null,
        .m_index = 0,
        .m_copy = null,
    },
    .m_name = "zigfafreplay",
    .m_doc = null,
    .m_size = -1,
    .m_methods = &Methods,
    .m_slots = null,
    .m_traverse = null,
    .m_clear = null,
    .m_free = null,
};

pub export fn PyInit_zigfafreplay() [*c]py.PyObject {
    py.Py_Initialize();
    return py.PyModule_Create(&module);
}
