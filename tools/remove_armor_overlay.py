from pathlib import Path

path = Path("fabric/fabric-core/src/client/java/com/hpfxd/spectatorplus/fabric/client/mixin/GuiMixin.java")
text = path.read_text()

old = "EquipmentSlot[] slots = {EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};"
new = "EquipmentSlot[] slots = {}; // Keep potion effects at the top-right without a redundant armor overlay."

if old not in text:
    raise SystemExit("BetterPOV armor-overlay replacement point not found")

path.write_text(text.replace(old, new, 1))
print("Removed BetterPOV top-right armor overlay")
