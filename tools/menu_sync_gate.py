from pathlib import Path


HANDLER = Path("paper/paper-core/src/main/java/com/hpfxd/spectatorplus/paper/sync/handler/screen/ScreenSyncHandler.java")


def replace_method(text: str, signature: str, replacement: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"method not found: {signature}")
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[:start] + replacement + text[index + 1:]
    raise SystemExit(f"unterminated method: {signature}")


text = HANDLER.read_text()

open_signature = "    private void openSyncedContainer(Player spectator, InventoryView targetView) {"
target_gate = """    private void openSyncedContainer(Player spectator, InventoryView targetView) {
        // Only a modded target can announce the exact client screen lifecycle.
        if (!(targetView.getPlayer() instanceof final Player target) || !this.hasScreenSyncClient(target)) {
            return;
        }
"""
open_start = text.find(open_signature)
open_prefix = text[open_start:open_start + 500] if open_start >= 0 else ""
if "this.hasScreenSyncClient(target)" not in open_prefix:
    if open_signature not in text:
        raise SystemExit("openSyncedContainer insertion point not found")
    text = text.replace(open_signature, target_gate, 1)

text = replace_method(text, "    public void onPlayerOpenInventory(Player target)", """    public void onPlayerOpenInventory(Player target) {
        if (!this.hasScreenSyncClient(target)) {
            return;
        }

        try {
            this.ignoreInventoryEvents = true;
            final InventoryView view = target.getOpenInventory();

            for (final Player spectator : this.plugin.getSyncController().getSpectators(target, PERMISSION)) {
                if (!this.canOverrideSpectatorView(spectator, spectator.getOpenInventory())) {
                    continue;
                }
                this.openSyncedContainer(spectator, view);
            }
        } finally {
            this.ignoreInventoryEvents = false;
        }
    }""")

text = replace_method(text, "    public void onOpen(InventoryOpenEvent event)", """    public void onOpen(InventoryOpenEvent event) {
        if (this.ignoreInventoryEvents || !(event.getPlayer() instanceof final Player target)) {
            return;
        }

        // Real containers use Paper lifecycle events. Require the target's registered
        // BetterPOV channel so vanilla targets never create blank mirrored menus.
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
    }""")

text = replace_method(text, "    public void onStartSpectating(PlayerStartSpectatingEntityEvent event)", """    public void onStartSpectating(PlayerStartSpectatingEntityEvent event) {
        final Player spectator = event.getPlayer();

        final SyncedScreen screen = this.screens.remove(spectator.getUniqueId());
        if (screen != null) {
            screen.close();
        }

        if (event.getNewSpectatorTarget() instanceof final Player target
                && spectator.hasPermission(PERMISSION)
                && this.hasScreenSyncClient(target)) {
            final InventoryView view = target.getOpenInventory();
            if (view.getType() != InventoryType.CRAFTING && view.getType() != InventoryType.CREATIVE) {
                Bukkit.getScheduler().runTask(this.plugin, () -> this.openSyncedContainer(spectator, view));
            }
        }
    }""")

helper = """    private boolean hasScreenSyncClient(Player player) {
        return player.getListeningPluginChannels().contains(ClientboundScreenSyncPacket.ID.asString());
    }

"""
if helper not in text:
    marker = "    private void sendContainerSnapshot(Player spectator, SyncedScreen screen)"
    if marker not in text:
        raise SystemExit("sendContainerSnapshot insertion point not found")
    text = text.replace(marker, helper + marker, 1)

HANDLER.write_text(text)
print("Applied target-capability-gated BetterPOV menu lifecycle sync")
