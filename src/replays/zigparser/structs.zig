const std = @import("std");
const Allocator = std.mem.Allocator;

const TableKeyContext = struct {
    // this is definitely wrong but it's good enough for our purposes
    pub fn hash(ctx: TableKeyContext, key: TableKey) u64 {
        _ = ctx;
        var hasher = std.hash.Wyhash.init(0);
        switch (key) {
            .string => |str| hasher.update(str),
            .number => |num| hasher.update(std.mem.asBytes(&num)),
        }
        return hasher.final();
    }

    pub fn eql(ctx: TableKeyContext, a: TableKey, b: TableKey) bool {
        _ = ctx;

        if (@intFromEnum(a) != @intFromEnum(b)) return false;
        return switch (a) {
            .string => |str| std.mem.eql(u8, str, b.string),
            .number => |num| num == b.number,
        };
    }
};

pub const TableKey = union(enum) {
    string: []const u8,
    number: f32,
};

pub const LuaTable = std.HashMap(TableKey, LuaValue, TableKeyContext, 80);
pub const LuaValue = union(enum) {
    const Self = @This();

    table: *LuaTable,
    string: []const u8,
    number: f32,
    boolean: bool,
    nil,

    pub fn as_bool(self: @This()) bool {
        switch (self) {
            .table => |table| {
                return table.count() > 0;
            },
            .string => |str| {
                return str.len > 0;
            },
            .number => {
                return true;
            },
            .nil => {
                return false;
            },
            .boolean => |value| {
                return value == true;
            },
        }
    }

    pub fn deinit(self: Self, allocator: Allocator) void {
        switch (self) {
            .table => |table| {
                deinit_lua_table(table, allocator);
            },
            else => {},
        }
    }
};

pub fn deinit_lua_table(table: *LuaTable, allocator: Allocator) void {
    var iterator = table.valueIterator();
    while (iterator.next()) |value| {
        value.deinit(allocator);
    }
    table.deinit();
    allocator.destroy(table);
}

pub const Chatline = struct {
    tick: u32,
    sender: []const u8,
    to: []const u8,
    text: []const u8,
    army_num: i32,
};

pub const Command = struct {
    const Self = @This();

    tick: u32,
    cmd_type: u8,
    blueprint: []const u8,
    upgrades: LuaValue,

    pub fn deinit(self: Self, allocator: Allocator) void {
        self.upgrades.deinit(allocator);
    }
};

pub const Point = struct {
    tick: u32,
    x: f32,
    y: f32,
    cmd_type: u8,
    source: u8,
};

pub const ReplayMetadata = struct {
    uid: u32,

    featured_mod: []const u8,
    title: []const u8,
    host: []const u8,

    launched_at: f64,
    game_end: ?f64 = null,
    game_time: ?f64 = null,

    version: u8 = 1,
    compression: []const u8 = "",
};

pub const Preprocessed = struct {
    metadata: std.json.Parsed(ReplayMetadata),
    data: []u8,

    pub fn deinit(self: @This(), allocator: Allocator) void {
        self.metadata.deinit();
        allocator.free(self.data);
    }
};

pub const ParseError = error{
    OutOfMemory,
    FileTooLong,
    SystemError,
    ValueError,
    Desync,
    InvalidReplay,
    NoSpaceLeft,
};

pub const PlayerGameStats = struct {
    defeated: ?f32 = null,
    type: []const u8,
    name: []const u8,
    faction: u8,
    general: struct {
        lastupdatetick: u32,
        score: u32,
        currentcap: f32,
        currentunits: f32,
        lost: GeneralStatsMetric,
        kills: GeneralStatsMetric,
        built: GeneralStatsMetric,
    },
    units: struct {
        air: UnitStat,
        land: UnitStat,
        naval: UnitStat,
        structures: UnitStat,
        tech1: UnitStat,
        tech2: UnitStat,
        tech3: UnitStat,
        experimental: UnitStat,
        transportation: UnitStat,
        cdr: UnitStat,
        sacu: UnitStat,
        engineer: UnitStat,
    },
    resources: struct {
        massin: struct {
            total: f64,
            reclaimed: f64,
        },
        massout: struct {
            total: f64,
            excess: f64,
        },
        energyin: struct {
            total: f64,
            reclaimed: f64,
        },
        energyout: struct {
            total: f64,
            excess: f64,
        },
    },

    pub const GeneralStatsMetric = struct {
        mass: f64,
        count: u32,
        energy: f64,
    };

    pub const UnitStat = struct {
        built: u32,
        lost: u32,
        kills: u32,
    };

    pub const UnitsStats = struct {
        air: UnitStat,
        land: UnitStat,
        naval: UnitStat,
        structures: UnitStat,
        tech1: UnitStat,
        tech2: UnitStat,
        tech3: UnitStat,
        experimental: UnitStat,
        transportation: UnitStat,
        cdr: UnitStat,
        sacu: UnitStat,
        engineer: UnitStat,
    };
};

pub const GameStats = struct {
    stats: []PlayerGameStats,
};
