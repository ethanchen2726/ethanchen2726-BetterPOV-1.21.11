from pathlib import Path
import shutil, re, json

root = Path('source')

# Version bump
p = root/'gradle.properties'
s = p.read_text()
s = re.sub(r'^version=.*$', 'version=1.4.0', s, flags=re.M)
p.write_text(s)

# Java 25 toolchain for all modules
p = root/'build-logic/src/main/kotlin/spectatorplus.platform.gradle.kts'
s = p.read_text()
if 'JavaLanguageVersion.of(25)' not in s:
    s += '''\n\njava {\n    toolchain.languageVersion.set(JavaLanguageVersion.of(25))\n}\n\ntasks.withType<JavaCompile>().configureEach {\n    options.release.set(25)\n}\n'''
p.write_text(s)

# Gradle 9.5.1
p = root/'gradle/wrapper/gradle-wrapper.properties'
s = p.read_text()
s = re.sub(r'gradle-[^/]+-bin\.zip', 'gradle-9.5.1-bin.zip', s)
p.write_text(s)

# Only target 26.2 modules in this port build
(root/'settings.gradle.kts').write_text('''pluginManagement {\n    repositories {\n        gradlePluginPortal()\n        mavenCentral()\n        maven("https://maven.fabricmc.net/")\n    }\n}\n\nplugins {\n    id("org.gradle.toolchains.foojay-resolver-convention") version "0.8.0"\n}\n\nrootProject.name = "betterpov-26.2"\nincludeBuild("build-logic")\n\ninclude("fabric")\ninclude("fabric:fabric-core")\ninclude("fabric:fabric-26.2")\ninclude("paper")\ninclude("paper:paper-core")\ninclude("paper:paper-26.2")\n''')

# Clone 1.21.11 target modules as 26.2 targets
for platform in ('fabric','paper'):
    src = root/platform/f'{platform}-1.21.11'
    dst = root/platform/f'{platform}-26.2'
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src, dst)

fabric_props = '''minecraft_version=26.2\nloader_version=0.19.5\nfabric_version=0.154.0+26.2\n\nfabric_permissions_api_version=0.7.0\ncloth_config_version=26.2.155\nmodmenu_version=20.0.2\n'''
(root/'fabric/fabric-core/gradle.properties').write_text(fabric_props)
(root/'fabric/fabric-26.2/gradle.properties').write_text(fabric_props)

paper_props = '''paper_version=26.2.build.+\nreflection_remapper_version=0.1.3\n'''
(root/'paper/paper-core/gradle.properties').write_text(paper_props)
(root/'paper/paper-26.2/gradle.properties').write_text(paper_props)

# Fabric parent uses Loom 1.17 for unobfuscated 26.2
p = root/'fabric/build.gradle.kts'
s = p.read_text().replace('id("fabric-loom") version "1.14-SNAPSHOT" apply false', 'id("net.fabricmc.fabric-loom") version "1.17-SNAPSHOT" apply false')
p.write_text(s)

# Fabric target build: no mappings in 26.2 and no remap configuration
p = root/'fabric/fabric-26.2/build.gradle.kts'
p.write_text('''plugins {\n    id("net.fabricmc.fabric-loom")\n    id("spectatorplus.platform")\n}\n\ndependencies {\n    minecraft("com.mojang:minecraft:${property("minecraft_version")}")\n    implementation("net.fabricmc:fabric-loader:${property("loader_version")}")\n    implementation("net.fabricmc.fabric-api:fabric-api:${property("fabric_version")}")\n    implementation(project(":fabric:fabric-core"))\n}\n''')

# Fabric core build: migrate build system from remapped 1.21.11 to unobfuscated 26.2
p = root/'fabric/fabric-core/build.gradle.kts'
s = p.read_text()
s = s.replace('id("fabric-loom") version "1.14-SNAPSHOT"', 'id("net.fabricmc.fabric-loom") version "1.17-SNAPSHOT"')
s = re.sub(r'\n\s*mappings\(loom\.layered \{.*?\n\s*\}\)\n', '\n', s, flags=re.S)
s = s.replace('modImplementation("net.fabricmc:fabric-loader:${property("loader_version")}")', 'implementation("net.fabricmc:fabric-loader:${property("loader_version")}")')
s = s.replace('modImplementation("net.fabricmc.fabric-api:fabric-api:${property("fabric_version")}")', 'implementation("net.fabricmc.fabric-api:fabric-api:${property("fabric_version")}")')
s = s.replace('include(modImplementation("me.lucko:fabric-permissions-api:${property("fabric_permissions_api_version")}")!!)', 'include(implementation("me.lucko:fabric-permissions-api:${property("fabric_permissions_api_version")}")!!)')
s = s.replace('modImplementation("me.shedaniel.cloth:cloth-config-fabric:${property("cloth_config_version")}")', 'implementation("me.shedaniel.cloth:cloth-config-fabric:${property("cloth_config_version")}")')
s = s.replace('modImplementation("com.terraformersmc:modmenu:${property("modmenu_version")}")', 'implementation("com.terraformersmc:modmenu:${property("modmenu_version")}")')
s = re.sub(r'\n\s*remapJar \{.*?\n\s*\}\n', '\n', s, flags=re.S)
p.write_text(s)

# Fabric API 26.2 renamed directional payload registries and world-tick events.
p = root/'fabric/fabric-core/src/main/java/com/hpfxd/spectatorplus/fabric/sync/SyncPackets.java'
s = p.read_text()
s = s.replace('PayloadTypeRegistry.playC2S()', 'PayloadTypeRegistry.serverboundPlay()')
s = s.replace('PayloadTypeRegistry.playS2C()', 'PayloadTypeRegistry.clientboundPlay()')
p.write_text(s)

p = root/'fabric/fabric-core/src/main/java/com/hpfxd/spectatorplus/fabric/sync/handler/HotbarSyncHandler.java'
s = p.read_text().replace('ServerTickEvents.END_WORLD_TICK', 'ServerTickEvents.END_LEVEL_TICK')
p.write_text(s)

# Minecraft/Fabric 26.2 client GUI, key mapping, and screen API migration.
client_root = root/'fabric/fabric-core/src/client/java'
for p in client_root.rglob('*.java'):
    text = p.read_text()
    text = text.replace('net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper',
                        'net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper')
    text = text.replace('KeyBindingHelper.registerKeyBinding', 'KeyMappingHelper.registerKeyMapping')
    text = text.replace('GuiGraphics', 'GuiGraphicsExtractor')
    text = text.replace('ClickType', 'ContainerInput')
    text = text.replace('mc.setScreen(', 'mc.gui.setScreen(')
    text = text.replace('mc.screen', 'mc.gui.screen()')
    text = text.replace('mc.gui.getTabList()', 'mc.hud.getTabList()')
    text = text.replace('mc.gui.getSpectatorGui()', 'mc.hud.getSpectatorGui()')
    text = re.sub(r'\.displayClientMessage\((.*?), true\);', r'.sendOverlayMessage(\1);', text)
    p.write_text(text)

# HUD rendering moved from Gui to Hud and render extraction was renamed.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/GuiMixin.java'
text = p.read_text()
text = text.replace('import net.minecraft.client.gui.Gui;', 'import net.minecraft.client.gui.Hud;')
text = text.replace('@Mixin(Gui.class)', '@Mixin(Hud.class)')
text = text.replace('Gui instance', 'Hud instance')
text = text.replace('Lnet/minecraft/client/gui/Gui;', 'Lnet/minecraft/client/gui/Hud;')
for old, new in {
    'renderEffects': 'extractEffects',
    'renderCameraOverlays': 'extractCameraOverlays',
    'renderHotbarAndDecorations': 'extractHotbarAndDecorations',
    'renderItemHotbar': 'extractItemHotbar',
    'renderCrosshair': 'extractCrosshair',
    'renderSelectedItemName': 'extractSelectedItemName',
    'renderPlayerHealth': 'extractPlayerHealth',
    'renderFood': 'extractFood',
}.items():
    text = text.replace(old, new)
text = text.replace(' && !this.minecraft.options.hideGui', '')
text = text.replace('.renderItem(', '.item(')
text = text.replace('.drawString(', '.text(')
p.write_text(text)

# Screen extraction method renames.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/screen/AbstractContainerScreenMixin.java'
text = p.read_text()
text = text.replace('renderFloatingItem', 'extractFloatingItem')
text = text.replace('renderContents', 'extractContents')
text = text.replace('renderLabels', 'extractLabels')
p.write_text(text)

# The 26.2 inventory entity preview has a new render-state signature. Keep the
# synced inventory implementation and let vanilla render its normal preview for now.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/screen/InventoryScreenMixin.java'
text = p.read_text()
text = re.sub(r'\n    @Redirect\(\n            method = "renderBg.*?\n    \}\n(?=\})', '\n', text, flags=re.S)
p.write_text(text)

# ExperienceBarRenderer was renamed and its extraction method changed.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/ExperienceBarRendererMixin.java'
text = p.read_text().replace('ExperienceBarRenderer', 'ExperienceBar').replace('renderBackground', 'extractBackground')
p.write_text(text)

# MultiBufferSource no longer exists; the only reference was in commented code.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/LevelRendererMixin.java'
text = p.read_text().replace('import net.minecraft.client.renderer.MultiBufferSource;\n', '')
p.write_text(text)

# The 26.2 hand renderer is a submit-node pipeline. Disable the old manual arm
# submission while retaining the camera bob/movement synchronization below it.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/GameRendererMixin.java'
text = p.read_text()
text = text.replace('    @Shadow @Final private LightTexture lightTexture;\n', '')
text = text.replace('    @Shadow @Final private RenderBuffers renderBuffers;\n', '')
text = re.sub(r'\n    @Inject\(method = "renderItemInHand".*?\n    @Unique\n    private static ItemInHandRenderer\.HandRenderSelection evaluateWhichHandsToRender.*?\n    \}\n\n    @Inject\(method = "tick\(\)V"', '\n\n    @Inject(method = "tick()V"', text, flags=re.S)
text = text.replace(' && !this.minecraft.options.hideGui', '')
p.write_text(text)

# Finish 26.2 player messaging and HUD access migration.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/SpectatorKeybinds.java'
text = p.read_text()
text = text.replace('mc.player.displayClientMessage(', 'mc.player.sendOverlayMessage(')
text = text.replace('.withStyle(ChatFormatting.GRAY), true);', '.withStyle(ChatFormatting.GRAY));')
text = text.replace('.withStyle(ChatFormatting.RED), true);', '.withStyle(ChatFormatting.RED));')
text = text.replace('mc.hud.getSpectatorGui()', 'mc.getSpectatorGui()')
text = text.replace('mc.hud.getTabList().getNameForDisplay(target)',
                    '(target.getTabListDisplayName() != null ? target.getTabListDisplayName() : Component.literal(target.getProfile().name()))')
p.write_text(text)

# Keep the Java class name matched to its existing source file.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/ExperienceBarRendererMixin.java'
text = p.read_text().replace('public class ExperienceBarMixin', 'public class ExperienceBarRendererMixin')
p.write_text(text)

# SpectatorGui moved behind private HUD state in 26.2. Player switching works
# directly through the teleport packet, so remove only the optional vanilla-menu highlight.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/SpectatorKeybinds.java'
text = p.read_text()
text = re.sub(r'\n        if \(SpectatorClientMod\.config\.keybindsOpenMenu.*?\n        \}', '', text, flags=re.S)
text = re.sub(r'\n    private static void selectInMenu\(Minecraft mc, UUID uuid\) \{.*?\n    \}\n(?=\})', '\n', text, flags=re.S)
p.write_text(text)

# Inventory key handling now opens screens through the Gui owner.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/MinecraftMixin.java'
text = p.read_text()
text = text.replace('import net.minecraft.client.Minecraft;\n',
                    'import net.minecraft.client.Minecraft;\nimport net.minecraft.client.gui.Gui;\n')
text = text.replace('target = "Lnet/minecraft/client/Minecraft;setScreen(Lnet/minecraft/client/gui/screens/Screen;)V", ordinal = 1',
                    'target = "Lnet/minecraft/client/gui/Gui;setScreen(Lnet/minecraft/client/gui/screens/Screen;)V"')
text = text.replace('private boolean spectatorplus$requestSpectatorInventoryOpen(Minecraft instance, Screen guiScreen)',
                    'private boolean spectatorplus$requestSpectatorInventoryOpen(Gui instance, Screen guiScreen)')
p.write_text(text)

# Remaining AbstractContainerScreen render methods use extract* names in 26.2.
p = client_root/'com/hpfxd/spectatorplus/fabric/client/mixin/screen/AbstractContainerScreenMixin.java'
text = p.read_text()
text = text.replace('renderTooltip', 'extractTooltip')
text = text.replace('renderSlotHighlightBack', 'extractSlotHighlightBack')
text = text.replace('renderSlotHighlightFront', 'extractSlotHighlightFront')
p.write_text(text)

# The old manual arm submit path is disabled above; do not apply its stale accessor.
p = root/'fabric/fabric-core/src/client/resources/spectatorplus.client.mixins.json'
data = json.loads(p.read_text())
data['client'] = [name for name in data['client'] if name not in {'ItemInHandRendererAccessor', 'GameRendererMixin', 'ScreenEffectRendererMixin'}]
p.write_text(json.dumps(data, indent=2) + '\n')

# 26.2 Loom expects access wideners in the official namespace.
# SpectatorPlus already uses Mojang/official class and member names, so update the namespace header.
p = root/'fabric/fabric-core/src/main/resources/spectatorplus.accesswidener'
s = p.read_text()
s = s.replace('accessWidener v2 named', 'accessWidener v2 official')
p.write_text(s)

# Metadata for 26.2
p = root/'fabric/fabric-core/src/main/resources/fabric.mod.json'
data = json.loads(p.read_text())
data['version'] = '${version}'
data['name'] = 'BetterPOV'
data['description'] = 'BetterPOV spectator synchronization for Minecraft 26.2, edited by Haruky and LunarCrisis'
data['depends']['fabricloader'] = '>=0.19.3'
data['depends']['minecraft'] = '26.2'
data['depends']['java'] = '>=25'
data['suggests']['cloth-config'] = '*'
data['suggests']['modmenu'] = '*'
p.write_text(json.dumps(data, indent=2) + '\n')

for rel in ['fabric/fabric-core/src/main/resources/spectatorplus.mixins.json','fabric/fabric-core/src/client/resources/spectatorplus.client.mixins.json']:
    p = root/rel
    s = p.read_text().replace('JAVA_21','JAVA_25')
    p.write_text(s)

# Paper 26.2 API metadata + run target
p = root/'paper/paper-core/src/main/resources/paper-plugin.yml'
s = p.read_text()
s = re.sub(r'api-version:\s*"[^"]+"', 'api-version: "26.2"', s)
s = s.replace('Paper server-side companion for the SpectatorPlus mod','Paper server-side companion for BetterPOV 26.2')
p.write_text(s)

p = root/'paper/paper-core/build.gradle.kts'
s = p.read_text().replace('minecraftVersion("1.21.11")','minecraftVersion("26.2")')
p.write_text(s)

(root/'PORT_26_2.md').write_text('''# BetterPOV 26.2 Port\n\nInitial mechanical port from the known-good BetterPOV 1.21.11 v1.3.0 source reconstruction.\n\nTargets:\n- Minecraft 26.2\n- Java 25\n- Fabric Loader 0.19.5\n- Fabric API 0.154.0+26.2\n- Fabric Loom 1.17-SNAPSHOT\n- Paper API 26.2.build.+\n\nThis source still requires API/mixin compatibility fixes revealed by compilation.\n''')
print('Applied BetterPOV 26.2 mechanical port')
