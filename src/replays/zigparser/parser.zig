const std = @import("std");

const structs = @import("structs.zig");
const utils = @import("utils.zig");

const Allocator = std.mem.Allocator;

const Chatline = structs.Chatline;
const Command = structs.Command;
const GameStats = structs.GameStats;
const Luatable = structs.LuaTable;
const LuaValue = structs.LuaValue;
const ParseError = structs.ParseError;
const PlayerGameStats = structs.PlayerGameStats;
const Point = structs.Point;
const ParseErorr = structs.ParseError;

const LUA_TYPE = @import("replayformat.zig").LUA_TYPE;
const STITARGET = @import("replayformat.zig").STITARGET;
const CommandType = @import("replayformat.zig").UnitCommandType;
const Operation = @import("replayformat.zig").Operation;

const SliceIterator = @import("sliceiterator.zig").SliceIterator;

pub fn parse(replay_buf: []u8, allocator: Allocator) ParseErorr!Parser {
    var iterator = SliceIterator.from_slice(replay_buf);
    var result = Parser.init(&iterator, allocator);
    errdefer result.deinit(allocator);
    try result.parse();
    return result;
}

pub const HeaderData = struct {
    const Self = @This();

    patch: []const u8,
    version: []const u8,
    mods: LuaValue,
    scenario_info: LuaValue,
    players: std.AutoHashMap(u8, []const u8),
    observers: std.AutoHashMap(usize, []const u8),
    armies: std.AutoHashMap(u8, LuaValue),
    random_seed: u32,

    pub fn init(allocator: Allocator) Self {
        return Self{
            .patch = "",
            .version = "",
            .mods = LuaValue.nil,
            .scenario_info = LuaValue.nil,
            .players = std.AutoHashMap(u8, []const u8).init(allocator),
            .observers = std.AutoHashMap(usize, []const u8).init(allocator),
            .armies = std.AutoHashMap(u8, LuaValue).init(allocator),
            .random_seed = 0,
        };
    }
    pub fn deinit(self: *Self, allocator: Allocator) void {
        self.players.deinit();
        self.observers.deinit();

        self.mods.deinit(allocator);
        self.scenario_info.deinit(allocator);

        var iterator = self.armies.valueIterator();
        while (iterator.next()) |value| {
            value.deinit(allocator);
        }
        self.armies.deinit();
    }
};

pub const BodyData = struct {
    const Self = @This();

    ticks: u32,
    commands: std.AutoHashMap(u8, std.ArrayList(Command)),
    points: std.ArrayList(Point),
    chatlines: std.ArrayList(Chatline),
    lastticks: std.AutoHashMap(u8, u32),
    chart_data: std.AutoHashMap(u8, std.ArrayList(u32)),
    game_stats: ?std.json.Parsed(GameStats) = null,

    pub fn init(allocator: Allocator) Self {
        return Self{
            .ticks = 0,
            .commands = std.AutoHashMap(u8, std.ArrayList(Command)).init(allocator),
            .points = std.ArrayList(Point).init(allocator),
            .chatlines = std.ArrayList(Chatline).init(allocator),
            .lastticks = std.AutoHashMap(u8, u32).init(allocator),
            .chart_data = std.AutoHashMap(u8, std.ArrayList(u32)).init(allocator),
        };
    }

    pub fn deinit(self: *Self, allocator: Allocator) void {
        var commands_iterator = self.commands.valueIterator();
        while (commands_iterator.next()) |array| {
            for (array.items) |command| {
                command.deinit(allocator);
            }
            array.*.deinit();
        }
        self.commands.deinit();

        self.points.deinit();
        self.chatlines.deinit();
        self.lastticks.deinit();

        var chart_iterator = self.chart_data.valueIterator();
        while (chart_iterator.next()) |chart_entry| {
            chart_entry.deinit();
        }
        self.chart_data.deinit();
        if (self.game_stats) |stats| {
            stats.deinit();
        }
    }
};

pub const Parser = struct {
    const Self = @This();

    player_source: ?u8 = null,
    prev_tick: ?u32 = null,
    prev_digest: ?[]const u8 = null,

    replay_buf: *SliceIterator,
    header_data: HeaderData,
    body_data: BodyData,

    allocator: Allocator,

    pub fn init(replay_buf: *SliceIterator, allocator: Allocator) Self {
        return Self{
            .replay_buf = replay_buf,
            .header_data = HeaderData.init(allocator),
            .body_data = BodyData.init(allocator),
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Self, allocator: Allocator) void {
        self.header_data.deinit(allocator);
        self.body_data.deinit(allocator);
    }

    pub fn pin_lasttick(self: *Self, player: u8) ParseError!void {
        try self.body_data.lastticks.put(player, self.body_data.ticks);
    }

    pub fn process_command_target(self: *Self, command_type: u8) ParseError!void {
        self.replay_buf.ignoreMany(4);
        const stitarget: STITARGET = @enumFromInt(self.replay_buf.next().?);

        switch (stitarget) {
            STITARGET.Position => {
                const x = utils.cast_float32(self.replay_buf.ptr[0..4]);
                const y = utils.cast_float32(self.replay_buf.ptr[8..12]);
                self.replay_buf.ignoreMany(4 * 3);
                try self.body_data.points.append(Point{
                    .tick = self.body_data.ticks,
                    .x = x,
                    .y = y,
                    .cmd_type = command_type,
                    .source = self.player_source.?,
                });
            },
            STITARGET.Entity => {
                self.replay_buf.ignoreMany(4);
            },
            STITARGET.NONE => {},
        }
    }

    pub fn append_chart_data(self: *Self, player: u8) ParseError!void {
        if (self.body_data.chart_data.getPtr(player)) |list| {
            try list.append(self.body_data.ticks);
        } else {
            var list = std.ArrayList(u32).init(self.allocator);
            try list.append(self.body_data.ticks);
            try self.body_data.chart_data.put(player, list);
        }
    }

    fn process_formation(self: *Self) void {
        const formation = self.replay_buf.read_int(i32);
        if (formation != -1) {
            self.replay_buf.ignoreMany(4 * 5);
        }
    }

    fn process_issue_command(self: *Self, player: u8) ParseError!void {
        const units_num = utils.cast_int(u32, self.replay_buf.ptr[0..4]);
        self.replay_buf.ignoreMany(4 * (units_num + 3));
        const cmd_type = self.replay_buf.next().?;

        try self.process_command_target(cmd_type);
        self.replay_buf.ignoreNext();
        self.process_formation();

        const blueprint = self.replay_buf.read_string();
        self.replay_buf.ignoreMany(4 * 3);
        const upgrades = try parse_next(self.replay_buf, self.allocator);
        if (upgrades.as_bool()) {
            self.replay_buf.ignoreNext();
        }
        if (self.body_data.commands.getPtr(player)) |commands_list| {
            try commands_list.append(.{
                .blueprint = blueprint,
                .cmd_type = cmd_type,
                .tick = self.body_data.ticks,
                .upgrades = upgrades,
            });
        }
    }

    fn append_chatline(self: *Self, lua: LuaValue) ParseError!void {
        if (!lua.table.contains(.{ .string = "Msg" })) {
            return;
        }
        const msg = lua.table.get(.{ .string = "Msg" }).?;

        const from_ = lua.table.get(.{ .string = "From" }).?.number - 1;
        const from: i8 = @intFromFloat(from_);
        if (from < 0 or self.header_data.armies.get(@as(u8, @intCast(from))) == null) {
            return;
        }

        const sender = lua.table.get(.{ .string = "Sender" });
        const to = msg.table.get(.{ .string = "to" });
        const text = msg.table.get(.{ .string = "text" });

        inline for ([3]?LuaValue{ sender, to, text }) |field| {
            if (field == null or std.meta.activeTag(field.?) != .string) {
                return;
            }
        }

        const army_table = self.header_data.armies.get(@as(u8, @intCast(from))).?.table;
        const player_name = army_table.get(.{ .string = "PlayerName" }).?.string;
        if (std.mem.eql(u8, sender.?.string, player_name)) {
            try self.body_data.chatlines.append(.{
                .tick = self.body_data.ticks,
                .sender = player_name,
                .to = to.?.string,
                .text = text.?.string,
                .army_num = from,
            });
        }
    }

    fn process_lua_sim_callback(self: *Self, callback_size: u16) ParseError!void {
        const left_before = self.replay_buf.len;

        const function = self.replay_buf.read_string();
        const lua = try parse_next(self.replay_buf, self.allocator);
        defer lua.deinit(self.allocator);

        const left_after = self.replay_buf.len;
        self.replay_buf.ignoreMany(callback_size - (left_before - left_after));

        if (std.mem.eql(u8, function, "GiveResourcesToPlayer")) {
            try self.append_chatline(lua);
        } else if (std.mem.eql(u8, function, "ModeratorEvent")) {
            try self.process_moderator_event(lua);
        }
    }

    fn process_moderator_event(self: *Self, lua: LuaValue) ParseError!void {
        if (self.body_data.game_stats != null) {
            return;
        }
        const message = lua.table.get(.{ .string = "Message" }).?.string;
        if (message.len > 35 and
            std.mem.eql(u8, message[0..35], "GpgNetSend with command 'JsonStats'"))
        {
            const parse_options: std.json.ParseOptions = .{
                .allocate = .alloc_always,
                .ignore_unknown_fields = true,
            };
            const game_stats = std.json.parseFromSlice(
                GameStats,
                self.allocator,
                message[46 .. message.len - 2],
                parse_options,
            ) catch return ParseError.ValueError;
            self.body_data.game_stats = game_stats;
        }
    }

    pub fn parse(self: *Self) ParseError!void {
        try self.parse_header();
        try self.parse_body();
    }

    pub fn parse_body(
        self: *Self,
    ) ParseError!void {
        for (0..self.header_data.players.count()) |i| {
            const list = std.ArrayList(Command).init(self.allocator);
            try self.body_data.commands.put(@as(u8, @intCast(i)), list);
        }
        const moved_cmd = @intFromEnum(CommandType.MovePreviouslyIssuedCommand);
        while (self.replay_buf.len > 0) {
            const message_op: Operation = @enumFromInt(self.replay_buf.next().?);
            const message_len = self.replay_buf.read_int(u16);

            switch (message_op) {
                .CMDST_Advance => {
                    self.body_data.ticks += self.replay_buf.read_uint32();
                },
                .CMDST_SetCommandSource => {
                    self.player_source = self.replay_buf.next().?;
                },
                .CMDST_CommandSourceTerminated => {
                    try self.pin_lasttick(self.player_source.?);
                },
                .CMDST_SetCommandTarget => {
                    try self.process_command_target(moved_cmd);
                },
                .CMDST_IssueCommand, .CMDST_IssueFactoryCommand => {
                    const player = self.player_source.?;
                    try self.append_chart_data(player);
                    try self.process_issue_command(player);
                },
                .CMDST_VerifyChecksum => {
                    try self.process_checksum();
                },
                .CMDST_LuaSimCallback => {
                    try self.process_lua_sim_callback(message_len - 3);
                },
                else => {
                    self.replay_buf.ignoreMany(message_len - 3);
                },
            }
        }
    }

    fn process_checksum(self: *Self) ParseError!void {
        const digest = self.replay_buf.ptr[0..16];
        const tick_num = utils.cast_int(u32, self.replay_buf.ptr[16..20]);

        if (self.prev_tick != null and
            self.prev_digest != null and
            tick_num == self.prev_tick and
            !std.mem.eql(u8, digest, self.prev_digest.?) and
            // game stats is sort of an indicator of game end
            self.body_data.game_stats == null)
        {
            return ParseError.Desync;
        }

        self.prev_digest = digest;
        self.prev_tick = tick_num;
        self.replay_buf.ignoreMany(20);
    }

    pub fn process_armies(self: *Self) ParseError!void {
        const num_armies: usize = self.replay_buf.next() orelse return ParseError.InvalidReplay;

        var ai_army_num: u8 = @intCast(self.header_data.players.count());
        for (0..num_armies) |_| {
            _ = self.replay_buf.read_uint32();
            const player_data = try parse_next(self.replay_buf, self.allocator);
            const player_source = self.replay_buf.next() orelse return ParseError.InvalidReplay;

            if (player_source == 255) {
                // ai armies
                const civilian = player_data.table.get(.{ .string = "Civilian" }) orelse {
                    return ParseError.InvalidReplay;
                };
                if (!civilian.boolean) {
                    try self.header_data.armies.put(ai_army_num, player_data);
                    ai_army_num += 1;
                } else {
                    player_data.deinit(self.allocator);
                }
            } else {
                // human armies
                try self.header_data.armies.put(player_source, player_data);
                self.replay_buf.ignoreNext();
            }
        }
    }

    pub fn process_players(self: *Self) ParseError!void {
        const num_sources: usize = self.replay_buf.next() orelse return ParseError.InvalidReplay;
        for (0..num_sources) |i| {
            const name = self.replay_buf.read_string();
            // according to other replay parsers' it is supposed to be player id
            // but unfortunately it is not
            const mystery = self.replay_buf.read_uint32();
            if (mystery == 0) {
                try self.header_data.observers.put(i, name);
            } else {
                try self.header_data.players.put(@as(u8, @intCast(i)), name);
            }
        }
    }

    pub fn parse_header(self: *Self) ParseError!void {
        self.header_data.patch = self.replay_buf.read_string();
        self.replay_buf.ignoreMany(3);

        self.header_data.version = self.replay_buf.read_string();
        self.replay_buf.ignoreMany(4);

        const mods_size: usize = @intCast(self.replay_buf.read_uint32());
        _ = &mods_size;
        self.header_data.mods = try parse_next(self.replay_buf, self.allocator);

        const scenario_size = self.replay_buf.read_uint32();
        _ = &scenario_size;
        self.header_data.scenario_info = try parse_next(self.replay_buf, self.allocator);

        try self.process_players();
        const cheats_enabled = (self.replay_buf.next() orelse return ParseError.InvalidReplay) == 1;
        _ = &cheats_enabled;
        try self.process_armies();
        self.header_data.random_seed = self.replay_buf.read_uint32();
    }
};

pub fn parse_next(
    buf: *SliceIterator,
    allocator: Allocator,
) ParseError!LuaValue {
    const lua_type: LUA_TYPE = @enumFromInt(buf.next().?);
    return try parse_next_as(buf, allocator, lua_type);
}

fn parse_next_as(
    buf: *SliceIterator,
    allocator: Allocator,
    lua_type: LUA_TYPE,
) ParseError!LuaValue {
    switch (lua_type) {
        .NUMBER => {
            return .{ .number = buf.read_float32() };
        },
        .STRING => {
            return .{ .string = buf.read_string() };
        },
        .NIL => {
            buf.ignoreNext();
            return LuaValue.nil;
        },
        .BOOL => {
            return .{ .boolean = buf.next().? == 1 };
        },
        .TABLE_START => {
            var contents = try allocator.create(Luatable);
            contents.* = Luatable.init(allocator);
            errdefer structs.deinit_lua_table(contents, allocator);

            while (buf.next()) |byte| {
                if (byte == @intFromEnum(LUA_TYPE.TABLE_END)) {
                    break;
                }
                const key_type: LUA_TYPE = @enumFromInt(byte);
                const key = try parse_next_as(buf, allocator, key_type);
                const value = try parse_next(buf, allocator);
                switch (key) {
                    .string => |str| {
                        try contents.put(.{ .string = str }, value);
                    },
                    .number => |num| {
                        try contents.put(.{ .number = num }, value);
                    },
                    else => {
                        return ParseError.ValueError;
                    },
                }
            }
            return .{ .table = contents };
        },
        else => {
            return .nil;
        },
    }
}
