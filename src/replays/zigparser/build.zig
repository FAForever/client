const std = @import("std");

const Translator = @import("translate_c").Translator;

pub fn build(b: *std.Build) void {
    const includepy = b.option([]const u8, "includepy", "Python API source").?;
    const libpy = b.option([]const u8, "libpy", "Python libdir").?;
    const syslibpy = b.option([]const u8, "syslibpy", "Python system lib name").?;

    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{ .preferred_optimize_mode = .fast });

    const translate_c = b.dependency("translate_c", .{});
    const translator: Translator = .init(translate_c, .{
        .c_source_file = b.path("py.h"),
        .target = target,
        .optimize = optimize,
        .link_system_libs = &.{
            .{ .name = syslibpy },
        },
    });
    translator.addIncludePath(.{ .cwd_relative = includepy });

    const lib = b.addLibrary(.{
        .name = "zigfafreplay",
        .linkage = .dynamic,
        .root_module = b.createModule(.{
            .root_source_file = b.path("zigfafreplay.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{.{
                .name = "py",
                .module = translator.mod,
            }},
        }),
    });
    lib.root_module.addLibraryPath(.{ .cwd_relative = libpy });

    b.installArtifact(lib);
}
