from pathlib import Path


path = Path(
    "paper/paper-core/src/main/java/com/hpfxd/spectatorplus/paper/"
    "sync/handler/screen/ScreenSyncHandler.java"
)
text = path.read_text()

old = """    public void onOpen(InventoryOpenEvent event) {
        // Paper events alone cannot prove that the target has BetterPOV Fabric.
        // Wait for ServerboundOpenedInventorySyncPacket from the target client so
        // vanilla targets never create blank or stuck mirrored menus.
    }
"""

new = """    public void onOpen(InventoryOpenEvent event) {
        if (this.ignoreInventoryEvents || !(event.getPlayer() instanceof final Player target)) {
            return;
        }

        // Real container screens are opened by the server and therefore do not use the
        // survival-inventory key packet. The registered BetterPOV channel is the capability
        // gate that prevents vanilla targets from creating blank mirrored menus.
        if (!this.hasScreenSyncClient(target)) {
            return;
        }

        try {
            this.ignoreInventoryEvents = true;
            for (final Player spectator : this.plugin.getSyncController().getSpectators(target, PERMISSION)) {
                if (!this.canOverrideSpectatorView(spectator, spectator.getOpenInventory())) {
                    continue;
                }
                this.openSyncedContainer(spectator, event.getView());
            }
        } finally {
            this.ignoreInventoryEvents = false;
        }
    }
"""

if old not in text:
    raise SystemExit("BetterPOV guarded container-open replacement point not found")

path.write_text(text.replace(old, new, 1))
print("Restored capability-gated Paper container open lifecycle")
