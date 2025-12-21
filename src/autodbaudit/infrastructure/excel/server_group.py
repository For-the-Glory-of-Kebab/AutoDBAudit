"""
Server Group Mixin Module.

Provides reusable server/instance grouping functionality with:
- Cell merging for Server and Instance columns
- Color rotation for server groups (Teal→Coral→Gold→Lavender)
- Shade alternation for instances within a server

Each sheet that uses this mixin gets its own isolated state via a dict keyed by sheet name.

UUID Support (v3):
    - Column A is now UUID (hidden)
    - Column B is Action indicator
    - Column C is Server
    - Column D is Instance
    - All column indices are +1 from pre-UUID layout
"""

from __future__ import annotations

from dataclasses import dataclass
from openpyxl.styles import PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from autodbaudit.infrastructure.excel_styles import (
    merge_server_cells,
    SERVER_GROUP_COLORS,
)


__all__ = ["ServerGroupMixin"]


@dataclass
class GroupState:
    """State for tracking server/instance grouping per sheet."""
    ws: Worksheet = None
    config: object = None
    last_server: str = ""
    last_instance: str = ""
    server_start_row: int = 2
    instance_start_row: int = 2
    server_idx: int = 0
    instance_alt: bool = False


class ServerGroupMixin:
    """
    Mixin providing server/instance grouping with merging and colors.
    
    Uses a dict to store per-sheet grouping state, avoiding conflicts
    when multiple sheets use this mixin.
    """
    
    def _init_grouping(self, ws: Worksheet, config) -> None:
        """Initialize grouping state for a sheet."""
        if not hasattr(self, '_grp_states'):
            self._grp_states = {}
        
        self._grp_states[config.name] = GroupState(
            ws=ws,
            config=config,
            last_server="",
            last_instance="",
            server_start_row=2,
            instance_start_row=2,
            server_idx=0,
            instance_alt=False,
        )
    
    def _get_state(self, config_name: str) -> GroupState:
        """Get grouping state for a sheet."""
        return self._grp_states.get(config_name)
    
    def _track_group(self, server_name: str, instance_name: str, config_name: str) -> str:
        """
        Track server/instance grouping and return row background color.
        
        Args:
            server_name: Server hostname
            instance_name: Instance name (empty string for default)
            config_name: Sheet config name to identify which state to use
        
        Returns:
            Hex color code for row background
        """
        state = self._grp_states[config_name]
        current_row = self._row_counters[config_name]
        inst_display = instance_name or "(Default)"
        
        # Check if SERVER changed
        if server_name != state.last_server:
            if state.last_server:
                self._merge_groups(config_name)
                state.server_idx += 1
            
            state.server_start_row = current_row
            state.instance_start_row = current_row
            state.last_server = server_name
            state.last_instance = inst_display
            state.instance_alt = False
        
        # Check if INSTANCE changed (within same server)
        elif inst_display != state.last_instance:
            self._merge_instance(config_name)
            state.instance_start_row = current_row
            state.last_instance = inst_display
            state.instance_alt = not state.instance_alt
        
        # Get color for this row
        color_main, color_light = SERVER_GROUP_COLORS[
            state.server_idx % len(SERVER_GROUP_COLORS)
        ]
        return color_main if state.instance_alt else color_light
    
    def _apply_row_color(
        self, 
        row: int, 
        color: str, 
        data_cols: list[int],
        ws: Worksheet,
    ) -> None:
        """Apply background color to specified columns AND Instance column."""
        fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        for col in data_cols:
            ws.cell(row=row, column=col).fill = fill
        # Instance column is 4 (A=UUID, B=Action, C=Server, D=Instance)
        ws.cell(row=row, column=4).fill = fill
    
    def _merge_instance(self, config_name: str) -> None:
        """Merge Instance cells for current instance group."""
        state = self._grp_states[config_name]
        current_row = self._row_counters[config_name]
        if current_row > state.instance_start_row:
            merge_server_cells(
                state.ws,
                server_col=4,  # Instance column (A=UUID, B=Action, C=Server, D=Instance)
                start_row=state.instance_start_row,
                end_row=current_row - 1,
                server_name=state.last_instance,
                is_alt=state.instance_alt,
            )
            # Always apply fill to merged instance cell
            color_main, color_light = SERVER_GROUP_COLORS[
                state.server_idx % len(SERVER_GROUP_COLORS)
            ]
            fill_color = color_main if state.instance_alt else color_light
            merged = state.ws.cell(row=state.instance_start_row, column=4)
            merged.fill = PatternFill(
                start_color=fill_color, end_color=fill_color, fill_type="solid"
            )
    
    def _merge_groups(self, config_name: str) -> None:
        """Merge both Server and Instance cells for current server group."""
        state = self._grp_states[config_name]
        
        # First merge the last instance group
        self._merge_instance(config_name)
        
        # Then merge the server group
        current_row = self._row_counters[config_name]
        if current_row > state.server_start_row:
            color_main, _ = SERVER_GROUP_COLORS[
                state.server_idx % len(SERVER_GROUP_COLORS)
            ]
            merge_server_cells(
                state.ws,
                server_col=3,  # Server column (A=UUID, B=Action, C=Server)
                start_row=state.server_start_row,
                end_row=current_row - 1,
                server_name=state.last_server,
                is_alt=True,
            )
            # Apply main color to merged server cell
            merged = state.ws.cell(row=state.server_start_row, column=3)
            merged.fill = PatternFill(
                start_color=color_main, end_color=color_main, fill_type="solid"
            )
    
    def _finalize_grouping(self, config_name: str) -> None:
        """Finalize by merging any remaining groups."""
        if hasattr(self, '_grp_states') and config_name in self._grp_states:
            state = self._grp_states[config_name]
            if state.last_server:
                self._merge_groups(config_name)
