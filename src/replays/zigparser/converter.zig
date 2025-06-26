const py = @cImport({
    @cDefine("PY_SSIZE_T_CLEAN", {});
    @cInclude("Python.h");
});

const std = @import("std");

const decoder = @import("decoder.zig");
const parser = @import("parser.zig");
const structs = @import("structs.zig");

pub fn py_simple(comptime T: type, value: T) [*c]py.PyObject {
    switch (T) {
        u8, u16, u32, usize => {
            return py.Py_BuildValue("i", value);
        },
        []const u8 => {
            return py.Py_BuildValue("s#", value.ptr, value.len);
        },
        f32, f64 => {
            return py.Py_BuildValue("f", value);
        },
        ?f32, ?f64 => {
            if (value) |not_null| {
                return py.Py_BuildValue("f", not_null);
            } else {
                return py.Py_BuildValue("");
            }
        },
        else => {
            return py.Py_BuildValue("");
        },
    }
}

pub fn convert_object(some_obj: anytype) [*c]py.PyObject {
    switch (@typeInfo(@TypeOf(some_obj))) {
        .@"struct" => {
            const dict = py.PyDict_New();
            inline for (std.meta.fields(@TypeOf(some_obj))) |field| {
                const value = convert_object(@field(some_obj, field.name));
                _ = py.PyDict_SetItemString(dict, field.name, value);
                py.Py_DecRef(value);
            }
            return dict;
        },
        .pointer => |ptr| {
            if (@typeInfo(ptr.child) == .@"struct") {
                const size: isize = @intCast(some_obj.len);
                const tuple = py.PyTuple_New(size);
                for (0.., some_obj) |i, obj| {
                    const value = convert_object(obj);
                    _ = py.PyTuple_SetItem(tuple, @as(isize, @intCast(i)), value);
                }
                return tuple;
            } else {
                return py_simple(@TypeOf(some_obj), some_obj);
            }
        },
        else => {
            return py_simple(@TypeOf(some_obj), some_obj);
        },
    }
}

pub fn convert_hashmap(hashmap: anytype) [*c]py.PyObject {
    const K = @FieldType(@TypeOf(hashmap).KV, "key");
    const V = @FieldType(@TypeOf(hashmap).KV, "value");

    const dict = py.PyDict_New();
    var iterator = hashmap.iterator();
    while (iterator.next()) |pair| {
        const key = py_simple(K, pair.key_ptr.*);
        var value: [*c]py.PyObject = undefined;
        switch (V) {
            structs.LuaValue => {
                value = convert_lua_value(pair.value_ptr.*);
            },
            else => {
                value = py_simple(V, pair.value_ptr.*);
            },
        }
        _ = py.PyDict_SetItem(dict, key, value);
        py.Py_DecRef(key);
        py.Py_DecRef(value);
    }
    return dict;
}

pub fn convert_points(replay_parser: parser.Parser) [*c]py.PyObject {
    const size: isize = @intCast(replay_parser.body_data.points.items.len);
    const my_list = py.PyList_New(size);
    for (0.., replay_parser.body_data.points.items) |i, item| {
        const tuple = py.Py_BuildValue(
            "(iffii)",
            item.tick,
            item.x,
            item.y,
            item.cmd_type,
            item.source,
        );
        _ = py.PyList_SetItem(my_list, @as(isize, @intCast(i)), tuple);
    }
    return my_list;
}

pub fn _convert_lua_table_key(table_key: structs.TableKey) [*c]py.PyObject {
    switch (table_key) {
        .string => |str| {
            return py_simple([]const u8, str);
        },
        .number => |num| {
            return py_simple(f32, num);
        },
    }
}

pub fn _convert_lua_table_value(table_value: structs.LuaValue) [*c]py.PyObject {
    switch (table_value) {
        .string => |str| {
            if (std.unicode.utf8ValidateSlice(str)) {
                return py_simple([]const u8, str);
            } else {
                return py_simple([]const u8, "non-utf8 nonsense");
            }
        },
        else => |val| {
            return convert_lua_value(val);
        },
    }
}

pub fn convert_lua_value(lua_value: structs.LuaValue) [*c]py.PyObject {
    switch (lua_value) {
        .table => |table| {
            const dict: [*c]py.PyObject = py.PyDict_New();
            _ = &table;
            var iterator = table.iterator();
            while (iterator.next()) |pair| {
                const key = _convert_lua_table_key(pair.key_ptr.*);
                const value = _convert_lua_table_value(pair.value_ptr.*);
                _ = py.PyDict_SetItem(dict, key, value);
                py.Py_DecRef(key);
                py.Py_DecRef(value);
            }
            return dict;
        },
        .string => |string| {
            return py_simple([]const u8, string);
        },
        .number => |number| {
            return py_simple(f32, number);
        },
        .boolean => |boolean| {
            return py_simple(u8, @as(u8, @intFromBool(boolean)));
        },
        .nil => {
            return py.Py_BuildValue("");
        },
    }
}

pub fn convert_commands(replay_parser: parser.Parser) [*c]py.PyObject {
    const commands_dict = py.PyDict_New();
    for (0..replay_parser.header_data.players.count()) |usize_player| {
        const player: u8 = @intCast(usize_player);
        const commands = replay_parser.body_data.commands.get(player).?;
        const tuple_size: isize = @intCast(commands.items.len);
        const commands_tuple = py.PyTuple_New(tuple_size);
        for (0.., commands.items) |i, item| {
            const dict = py.Py_BuildValue(
                "{s:i,s:i,s:s}",
                "tick",
                item.tick,
                "cmd_type",
                item.cmd_type,
                "blueprint",
                item.blueprint.ptr,
            );
            const upgrade = convert_lua_value(item.upgrades);
            _ = py.PyDict_SetItemString(dict, "upgrades", upgrade);
            py.Py_DecRef(upgrade);
            _ = py.PyTuple_SetItem(commands_tuple, @as(isize, @intCast(i)), dict);
        }
        _ = py.PyDict_SetItem(commands_dict, py_simple(u8, player), commands_tuple);
        py.Py_DecRef(commands_tuple);
    }
    return commands_dict;
}

pub fn convert_chatlines(replay_parser: parser.Parser) [*c]py.PyObject {
    const size: isize = @intCast(replay_parser.body_data.chatlines.items.len);
    const chatlines: [*c]py.PyObject = py.PyTuple_New(size);
    for (0.., replay_parser.body_data.chatlines.items) |i, item| {
        const line = py.Py_BuildValue(
            "(isssi)",
            item.tick,
            item.sender.ptr,
            item.to.ptr,
            item.text.ptr,
            item.army_num,
        );
        _ = py.PyTuple_SetItem(chatlines, @as(isize, @intCast(i)), line);
    }
    return chatlines;
}

pub fn convert_chart_data(replay_parser: parser.Parser) [*c]py.PyObject {
    const dict = py.PyDict_New();
    var iterator = replay_parser.body_data.chart_data.iterator();
    while (iterator.next()) |pair| {
        const key = py_simple(u8, pair.key_ptr.*);
        const items = pair.value_ptr.*.items;
        const size: isize = @intCast(items.len);
        const ticks_tuple = py.PyTuple_New(size);
        for (0.., items) |i, tick| {
            _ = py.PyTuple_SetItem(
                ticks_tuple,
                @as(isize, @intCast(i)),
                py_simple(u32, tick),
            );
        }
        _ = py.PyDict_SetItem(dict, key, ticks_tuple);
        py.Py_DecRef(key);
        py.Py_DecRef(ticks_tuple);
    }
    return dict;
}

pub fn convert_gamestats(replay_parser: parser.Parser) [*c]py.PyObject {
    if (replay_parser.body_data.game_stats) |game_stats| {
        return convert_object(game_stats.value);
    }
    return py.Py_BuildValue("");
}

pub fn convert_header(replay_parser: parser.Parser) [*c]py.PyObject {
    const dict: [*c]py.PyObject = py.PyDict_New();
    const dict_keys = [_][*c]const u8{
        "patch",
        "version",
        "mods",
        "scenario_info",
        "players",
        "observers",
        "armies",
        "random_seed",
    };

    const dict_values = [_][*c]py.PyObject{
        py_simple([]const u8, replay_parser.header_data.patch),
        py_simple([]const u8, replay_parser.header_data.version),
        convert_lua_value(replay_parser.header_data.mods),
        convert_lua_value(replay_parser.header_data.scenario_info),
        convert_hashmap(replay_parser.header_data.players),
        convert_hashmap(replay_parser.header_data.observers),
        convert_hashmap(replay_parser.header_data.armies),
        py_simple(u32, replay_parser.header_data.random_seed),
    };
    inline for (dict_keys, dict_values) |key, value| {
        _ = py.PyDict_SetItemString(dict, key, value);
        py.Py_DecRef(value);
    }
    return dict;
}

pub fn convert_body(replay_parser: parser.Parser) [*c]py.PyObject {
    const dict: [*c]py.PyObject = py.PyDict_New();
    const dict_keys = [_][*c]const u8{
        "ticks",
        "commands",
        "points",
        "chatlines",
        "lasttick",
        "chart_data",
        "game_stats",
    };
    const dict_values = [_][*c]py.PyObject{
        py_simple(u32, replay_parser.body_data.ticks),
        convert_commands(replay_parser),
        convert_points(replay_parser),
        convert_chatlines(replay_parser),
        convert_hashmap(replay_parser.body_data.lastticks),
        convert_chart_data(replay_parser),
        convert_gamestats(replay_parser),
    };
    inline for (dict_keys, dict_values) |key, value| {
        _ = py.PyDict_SetItemString(dict, key, value);
        py.Py_DecRef(value);
    }
    return dict;
}

pub fn convert_replaydata(replay_parser: parser.Parser) [*c]py.PyObject {
    const header = convert_header(replay_parser);
    const body = convert_body(replay_parser);
    const dict: [*c]py.PyObject = py.PyDict_New();
    _ = py.PyDict_SetItemString(dict, "header", header);
    _ = py.PyDict_SetItemString(dict, "body", body);
    py.Py_DecRef(header);
    py.Py_DecRef(body);
    return dict;
}

pub fn convert_full(replay_parser: parser.Parser, metadata: structs.ReplayMetadata) [*c]py.PyObject {
    const dict = py.PyDict_New();
    const simdata = convert_replaydata(replay_parser);
    const meta_data = convert_object(metadata);
    _ = py.PyDict_SetItemString(dict, "replaydata", simdata);
    _ = py.PyDict_SetItemString(dict, "metadata", meta_data);
    py.Py_DecRef(simdata);
    py.Py_DecRef(meta_data);
    return dict;
}
