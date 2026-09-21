from pathlib import Path


path = Path(
    "paper/paper-core/src/main/java/com/hpfxd/spectatorplus/paper/"
    "sync/handler/screen/ScreenSyncHandler.java"
)
text = path.read_text()

old = """                if (screen instanceof SyncedContainer) {
                    this.sendContainerSnapshot(screen.spectator, screen);
                }
                screen.update();
            } catch (Exception e) {
                this.plugin.getSLF4JLogger().warn(\"An exception occurred while updating a synced screen for \\\"{}\\\"\", screen.spectator.getName(), e);
            }
"""

new = """                if (screen instanceof SyncedContainer) {
                    this.sendContainerSnapshot(screen.spectator, screen);
                }

                // Survival inventory screens are rendered entirely by BetterPOV Fabric. Paper never
                // opens a Bukkit replica for them, so spectatorView is intentionally null. Their live
                // contents are delivered by sendContainerSnapshot() above.
                if (!screen.isSurvivalInventory()) {
                    screen.update();
                }
            } catch (Exception e) {
                // A broken entry must not be retried every tick and flood the server console.
                this.screens.remove(screen.spectator.getUniqueId());
                try {
                    screen.close();
                } catch (Exception closeException) {
                    e.addSuppressed(closeException);
                }
                this.plugin.getSLF4JLogger().warn(
                        \"Removed broken synced screen for \\\"\" + screen.spectator.getName() + \"\\\" after an update failure\",
                        e
                );
            }
"""

if old not in text:
    raise SystemExit("BetterPOV screen-tick NPE replacement point not found")

path.write_text(text.replace(old, new, 1))
print("Fixed BetterPOV survival-inventory tick NPE and repeated-failure cleanup")
