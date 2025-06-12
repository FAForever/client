pub const Operation = enum(u8) {
    CMDST_Advance,
    // uint32 - number of beats to advance.

    CMDST_SetCommandSource,
    // uint8 - command source

    CMDST_CommandSourceTerminated,
    // no args.

    CMDST_VerifyChecksum,
    // MD5Digest - checksum
    // uint32 - beat number

    CMDST_RequestPause,
    CMDST_Resume,
    CMDST_SingleStep,
    // All with no additional data.

    CMDST_CreateUnit,
    // uint8 - army index
    // string - blueprint ID
    // float - x
    // float - z
    // float - heading

    CMDST_CreateProp,
    // string - blueprint ID
    // Vector3f - location

    CMDST_DestroyEntity,
    // EntId - entity

    CMDST_WarpEntity,
    // EntId - entity
    // VTransform - new transform

    CMDST_ProcessInfoPair,
    // EntId - entity
    // string - arg1
    // string - arg2

    CMDST_IssueCommand,
    // uint32 - num units
    // EntIdSet - units
    // CmdData - command data
    // uint8 - clear queue flag

    CMDST_IssueFactoryCommand,
    // uint32 - num factories
    // EntIdSet - factories
    // CmdData - command data
    // uint8 - clear queue flag

    CMDST_IncreaseCommandCount,
    // CmdId - command id
    // int32 - count delta

    CMDST_DecreaseCommandCount,
    // CmdId - command id
    // int32 - count delta

    CMDST_SetCommandTarget,
    // CmdId - command id
    // STITarget - target

    CMDST_SetCommandType,
    // CmdId - command id
    // EUnitCommandType - type

    CMDST_SetCommandCells,
    // CmdId - command id
    // ListOfCells - list of cells
    // Vector3f - pos

    CMDST_RemoveCommandFromQueue,
    // CmdId - command id
    // EntId - unit

    CMDST_DebugCommand,
    // string -- the debug command string
    // Vector3f -- mouse pos (in world coords)
    // uint8 -- focus army index
    // EntIdSet -- selection

    CMDST_ExecuteLuaInSim,
    // string -- the lua string to evaluate in the sim state

    CMDST_LuaSimCallback,
    // string - callback function name
    // LuaObject - table of function arguments

    CMDST_EndGame,
    // no args.

    _,
};

pub const STITARGET = enum(u8) {
    NONE,
    Entity,
    Position,
};

pub const LUA_TYPE = enum(i8) {
    NUMBER,
    STRING,
    NIL,
    BOOL,
    TABLE_START,
    TABLE_END,
};

pub const UnitCommandType = enum(u8) {
    NONE,
    Stop,
    Move,
    Dive,
    FormMove,
    BuildSiloTactical,
    BuildSiloNuke,
    BuildFactory,
    BuildMobile,
    BuildAssist,
    Attack,
    FormAttack,
    Nuke,
    Tactical,
    Teleport,
    Guard,
    Patrol,
    Ferry,
    FormPatrol,
    Reclaim,
    Repair,
    Capture,
    TransportLoadUnits,
    TransportReverseLoadUnits,
    TransportUnloadUnits,
    TransportUnloadSpecificUnits,
    DetachFromTransport,
    Upgrade,
    Script,
    AssistCommander,
    KillSelf,
    DestroySelf,
    Sacrifice,
    Pause,
    OverCharge,
    AggressiveMove,
    FormAggressiveMove,
    AssistMove,
    SpecialAction,
    Dock,
    // artificially made up
    MovePreviouslyIssuedCommand,
    _
};
