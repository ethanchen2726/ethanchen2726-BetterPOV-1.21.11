from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    if old not in text:
        raise SystemExit(f"{label} replacement point not found in {path}")
    path.write_text(text.replace(old, new, 1))


client_root = Path("fabric/fabric-core/src/client/java/com/hpfxd/spectatorplus/fabric/client")

# A successfully created synced container used to fall through into the failure
# cleanup, which cleared syncData.screen and sent a close packet immediately.
menu_mixin = client_root / "mixin/screen/MenuScreensMixin.java"
replace_once(
    menu_mixin,
    """                }
            }

            // Unable to open, immediately tell the server we've closed this screen.
""",
    """                }
            }

            // A synced container was created successfully. Do not fall through into
            // the failure cleanup below or its contents will be cleared immediately.
            if (ScreenSyncController.syncedScreen != null) {
                return;
            }

            // Unable to open, immediately tell the server we've closed this screen.
""",
    "successful synced-container return",
)

# Paper sends complete container snapshots. A null Bukkit slot therefore means
# empty, not “leave the previous item unchanged”.
screen_data = client_root / "sync/screen/ScreenSyncData.java"
replace_once(
    screen_data,
    """        for (int i = 0; i < items.length && i < containerItems.size(); i++) {
            updateContainerItem(i, items[i]);
        }
""",
    """        for (int i = 0; i < items.length && i < containerItems.size(); i++) {
            final ItemStack item = items[i];
            containerItems.set(i, item == null || item.isEmpty() ? ItemStack.EMPTY : item);
        }
""",
    "full container snapshot empty-slot handling",
)

print("Fixed BetterPOV container contents lifecycle and empty-slot synchronization")
