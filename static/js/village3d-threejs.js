/**
 * Webwölfe - Three.js Village Renderer
 * 
 * Immersive 3D village visualization with:
 * - Day/night cycle with dynamic lighting
 * - Animated characters around campfire
 * - Visual hint effects (glowing eyes, shadows, etc.)
 * - Atmospheric effects (fog, particles)
 * 
 * SECURITY: Only receives visual data from server, no game state
 */

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

// Theme colors from logo palette
const THEME = {
    void: 0x0A0606,
    blood: 0x950706,
    crimson: 0x941814,
    ash: 0x332A29,
    stone: 0x6C5D5B,
    fire: 0xFF6B35,
    fireGlow: 0xFF9F1C,
    moonlight: 0xE8E8FF,
    starlight: 0xFFFFEE,
    grass: 0x1a2f1a,
    wood: 0x4a3728,
};

class Village3D {
    constructor(containerId, raumCode) {
        this.container = document.getElementById(containerId);
        this.raumCode = raumCode;
        this.players = [];
        this.isNight = true;
        this.animationId = null;
        this.clock = new THREE.Clock();
        this.hints = [];
        
        if (!this.container) {
            console.warn('Village3D container not found:', containerId);
            return;
        }
        
        this.init();
    }
    
    init() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight || 400;
        
        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(THEME.void);
        this.scene.fog = new THREE.FogExp2(THEME.void, 0.015);
        
        // Camera - isometric-style perspective
        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        this.camera.position.set(0, 15, 20);
        this.camera.lookAt(0, 0, 0);
        
        // Renderer
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true 
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;
        this.container.appendChild(this.renderer.domElement);
        
        // Create scene elements
        this.createGround();
        this.createCampfire();
        this.createSky();
        this.createLights();
        this.createForest();
        
        // Start animation loop
        this.animate();
        
        // Handle resize
        window.addEventListener('resize', () => this.onResize());
        
        // Initial data fetch
        this.fetchVillageData();
    }
    
    createGround() {
        // Main ground plane
        const groundGeometry = new THREE.CircleGeometry(25, 64);
        const groundMaterial = new THREE.MeshStandardMaterial({
            color: THEME.grass,
            roughness: 0.9,
            metalness: 0.0,
        });
        this.ground = new THREE.Mesh(groundGeometry, groundMaterial);
        this.ground.rotation.x = -Math.PI / 2;
        this.ground.receiveShadow = true;
        this.scene.add(this.ground);
        
        // Village circle (stone path)
        const pathGeometry = new THREE.RingGeometry(5, 6, 32);
        const pathMaterial = new THREE.MeshStandardMaterial({
            color: THEME.stone,
            roughness: 0.8,
        });
        const path = new THREE.Mesh(pathGeometry, pathMaterial);
        path.rotation.x = -Math.PI / 2;
        path.position.y = 0.01;
        path.receiveShadow = true;
        this.scene.add(path);
    }
    
    createCampfire() {
        // Fire base (logs)
        const logGeometry = new THREE.CylinderGeometry(0.1, 0.1, 1, 8);
        const logMaterial = new THREE.MeshStandardMaterial({ color: THEME.wood });
        
        for (let i = 0; i < 5; i++) {
            const log = new THREE.Mesh(logGeometry, logMaterial);
            const angle = (i / 5) * Math.PI * 2;
            log.position.set(Math.cos(angle) * 0.3, 0.1, Math.sin(angle) * 0.3);
            log.rotation.z = Math.PI / 2;
            log.rotation.y = angle;
            log.castShadow = true;
            this.scene.add(log);
        }
        
        // Fire particles (simple cones)
        this.fireParticles = [];
        const fireGeometry = new THREE.ConeGeometry(0.15, 0.5, 4);
        
        for (let i = 0; i < 8; i++) {
            const fireMaterial = new THREE.MeshBasicMaterial({
                color: i % 2 === 0 ? THEME.fire : THEME.fireGlow,
                transparent: true,
                opacity: 0.9,
            });
            const flame = new THREE.Mesh(fireGeometry, fireMaterial);
            const angle = (i / 8) * Math.PI * 2;
            flame.position.set(
                Math.cos(angle) * 0.2,
                0.3,
                Math.sin(angle) * 0.2
            );
            this.fireParticles.push({
                mesh: flame,
                baseY: 0.3,
                phase: i * 0.5,
            });
            this.scene.add(flame);
        }
        
        // Fire point light
        this.fireLight = new THREE.PointLight(THEME.fireGlow, 2, 15);
        this.fireLight.position.set(0, 0.5, 0);
        this.fireLight.castShadow = true;
        this.scene.add(this.fireLight);
    }
    
    createSky() {
        // Star field
        this.stars = [];
        const starGeometry = new THREE.SphereGeometry(0.05, 4, 4);
        const starMaterial = new THREE.MeshBasicMaterial({ color: THEME.starlight });
        
        for (let i = 0; i < 200; i++) {
            const star = new THREE.Mesh(starGeometry, starMaterial.clone());
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI / 2;
            const r = 50 + Math.random() * 30;
            
            star.position.set(
                r * Math.sin(phi) * Math.cos(theta),
                r * Math.cos(phi) + 10,
                r * Math.sin(phi) * Math.sin(theta)
            );
            star.material.opacity = Math.random() * 0.5 + 0.5;
            star.material.transparent = true;
            this.stars.push({
                mesh: star,
                phase: Math.random() * Math.PI * 2,
            });
            this.scene.add(star);
        }
        
        // Moon
        const moonGeometry = new THREE.SphereGeometry(2, 32, 32);
        const moonMaterial = new THREE.MeshBasicMaterial({
            color: THEME.moonlight,
            transparent: true,
            opacity: 0.9,
        });
        this.moon = new THREE.Mesh(moonGeometry, moonMaterial);
        this.moon.position.set(20, 25, -30);
        this.scene.add(this.moon);
        
        // Moon glow
        const moonGlowGeometry = new THREE.SphereGeometry(3, 32, 32);
        const moonGlowMaterial = new THREE.MeshBasicMaterial({
            color: THEME.moonlight,
            transparent: true,
            opacity: 0.2,
        });
        const moonGlow = new THREE.Mesh(moonGlowGeometry, moonGlowMaterial);
        this.moon.add(moonGlow);
    }
    
    createLights() {
        // Ambient light (very dim for night)
        this.ambientLight = new THREE.AmbientLight(0x111122, 0.3);
        this.scene.add(this.ambientLight);
        
        // Moonlight (directional)
        this.moonLight = new THREE.DirectionalLight(THEME.moonlight, 0.3);
        this.moonLight.position.set(20, 25, -30);
        this.moonLight.castShadow = true;
        this.moonLight.shadow.mapSize.width = 2048;
        this.moonLight.shadow.mapSize.height = 2048;
        this.scene.add(this.moonLight);
        
        // Sun light (for day mode)
        this.sunLight = new THREE.DirectionalLight(0xFFFFDD, 0);
        this.sunLight.position.set(-20, 30, 20);
        this.sunLight.castShadow = true;
        this.scene.add(this.sunLight);
    }
    
    createForest() {
        // Simple tree silhouettes around the clearing
        const treeGeometry = new THREE.ConeGeometry(1.5, 6, 6);
        const treeMaterial = new THREE.MeshStandardMaterial({
            color: 0x0a1a0a,
            roughness: 1.0,
        });
        const trunkGeometry = new THREE.CylinderGeometry(0.2, 0.3, 1.5, 6);
        const trunkMaterial = new THREE.MeshStandardMaterial({
            color: THEME.wood,
        });
        
        for (let i = 0; i < 30; i++) {
            const angle = (i / 30) * Math.PI * 2;
            const radius = 18 + Math.random() * 8;
            const x = Math.cos(angle) * radius;
            const z = Math.sin(angle) * radius;
            
            const tree = new THREE.Mesh(treeGeometry, treeMaterial);
            tree.position.set(x, 3 + Math.random(), z);
            tree.scale.set(
                0.8 + Math.random() * 0.4,
                0.8 + Math.random() * 0.4,
                0.8 + Math.random() * 0.4
            );
            tree.castShadow = true;
            this.scene.add(tree);
            
            const trunk = new THREE.Mesh(trunkGeometry, trunkMaterial);
            trunk.position.set(x, 0.75, z);
            this.scene.add(trunk);
        }
    }
    
    createPlayerAvatar(name, index, total, isAlive = true) {
        const group = new THREE.Group();
        
        // Calculate position in circle around campfire
        const angle = (index / total) * Math.PI * 2 - Math.PI / 2;
        const radius = 5.5;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;
        
        // Body (simple capsule shape)
        const bodyGeometry = new THREE.CapsuleGeometry(0.3, 0.6, 4, 8);
        const bodyMaterial = new THREE.MeshStandardMaterial({
            color: isAlive ? THEME.stone : 0x333333,
            roughness: 0.7,
        });
        const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
        body.position.y = 0.6;
        body.castShadow = true;
        group.add(body);
        
        // Head
        const headGeometry = new THREE.SphereGeometry(0.25, 16, 16);
        const headMaterial = new THREE.MeshStandardMaterial({
            color: isAlive ? 0xE0C8B8 : 0x888888,
            roughness: 0.6,
        });
        const head = new THREE.Mesh(headGeometry, headMaterial);
        head.position.y = 1.2;
        head.castShadow = true;
        group.add(head);
        
        // Eyes (for hint effects)
        const eyeGeometry = new THREE.SphereGeometry(0.04, 8, 8);
        const eyeMaterial = new THREE.MeshBasicMaterial({ color: 0x222222 });
        
        const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial.clone());
        leftEye.position.set(-0.08, 1.22, 0.22);
        leftEye.name = 'leftEye';
        group.add(leftEye);
        
        const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial.clone());
        rightEye.position.set(0.08, 1.22, 0.22);
        rightEye.name = 'rightEye';
        group.add(rightEye);
        
        // Name label (using sprite)
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'rgba(0,0,0,0.7)';
        ctx.roundRect(0, 16, 256, 40, 8);
        ctx.fill();
        ctx.font = 'bold 24px Arial';
        ctx.textAlign = 'center';
        ctx.fillStyle = isAlive ? '#FFFFFF' : '#888888';
        ctx.fillText(name, 128, 44);
        
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ 
            map: texture,
            transparent: true,
        });
        const nameSprite = new THREE.Sprite(spriteMaterial);
        nameSprite.position.y = 1.8;
        nameSprite.scale.set(2, 0.5, 1);
        group.add(nameSprite);
        
        // Position and rotate to face center
        group.position.set(x, 0, z);
        group.lookAt(0, 0, 0);
        
        // Store reference for animations
        group.userData = {
            name: name,
            isAlive: isAlive,
            index: index,
            angle: angle,
            baseY: 0,
            breathPhase: Math.random() * Math.PI * 2,
        };
        
        return group;
    }
    
    updatePlayers(playerData) {
        // Remove old player meshes
        this.players.forEach(p => this.scene.remove(p));
        this.players = [];
        
        // Create new player avatars
        const total = playerData.length;
        playerData.forEach((player, index) => {
            const avatar = this.createPlayerAvatar(
                player.name,
                index,
                total,
                player.ist_am_leben
            );
            this.players.push(avatar);
            this.scene.add(avatar);
        });
    }
    
    setTimeOfDay(isNight) {
        this.isNight = isNight;
        
        // Animate lighting transition
        const targetAmbient = isNight ? 0.3 : 1.0;
        const targetMoon = isNight ? 0.3 : 0;
        const targetSun = isNight ? 0 : 1.5;
        const targetFire = isNight ? 2 : 0.5;
        const targetBg = isNight ? THEME.void : 0x87CEEB;
        const targetFog = isNight ? 0.015 : 0.005;
        
        // Simple transition (could use GSAP for smoother)
        this.ambientLight.intensity = targetAmbient;
        this.moonLight.intensity = targetMoon;
        this.sunLight.intensity = targetSun;
        this.fireLight.intensity = targetFire;
        this.scene.background = new THREE.Color(targetBg);
        this.scene.fog.density = targetFog;
        
        // Toggle star visibility
        this.stars.forEach(star => {
            star.mesh.visible = isNight;
        });
        this.moon.visible = isNight;
    }
    
    showHint(playerName, hintType) {
        // Find player avatar
        const player = this.players.find(p => p.userData.name === playerName);
        if (!player) return;
        
        const hint = {
            player: player,
            type: hintType,
            startTime: this.clock.getElapsedTime(),
            duration: 1.5,
        };
        
        this.hints.push(hint);
        
        // Apply initial effect
        switch (hintType) {
            case 'augen_flackern':
                this.startEyeFlicker(player);
                break;
            case 'schatten':
                this.startShadowEffect(player);
                break;
            case 'mond_schein':
                this.startMoonbeamEffect(player);
                break;
            case 'nervoes':
                player.userData.isNervous = true;
                break;
        }
    }
    
    startEyeFlicker(player) {
        const leftEye = player.getObjectByName('leftEye');
        const rightEye = player.getObjectByName('rightEye');
        
        if (leftEye && rightEye) {
            leftEye.material.color.set(THEME.blood);
            rightEye.material.color.set(THEME.blood);
            leftEye.material.emissive = new THREE.Color(THEME.blood);
            rightEye.material.emissive = new THREE.Color(THEME.blood);
            leftEye.material.emissiveIntensity = 2;
            rightEye.material.emissiveIntensity = 2;
            
            // Reset after effect
            setTimeout(() => {
                leftEye.material.color.set(0x222222);
                rightEye.material.color.set(0x222222);
                leftEye.material.emissiveIntensity = 0;
                rightEye.material.emissiveIntensity = 0;
            }, 300);
        }
    }
    
    startShadowEffect(player) {
        // Create temporary shadow mesh
        const shadowGeometry = new THREE.PlaneGeometry(3, 3);
        const shadowMaterial = new THREE.MeshBasicMaterial({
            color: 0x000000,
            transparent: true,
            opacity: 0,
            side: THREE.DoubleSide,
        });
        const shadow = new THREE.Mesh(shadowGeometry, shadowMaterial);
        shadow.position.copy(player.position);
        shadow.position.y = 0.02;
        shadow.rotation.x = -Math.PI / 2;
        this.scene.add(shadow);
        
        // Animate shadow
        let opacity = 0;
        const animate = () => {
            opacity += 0.05;
            if (opacity <= 0.5) {
                shadow.material.opacity = opacity;
                requestAnimationFrame(animate);
            } else {
                // Fade out
                const fadeOut = () => {
                    opacity -= 0.05;
                    shadow.material.opacity = opacity;
                    if (opacity > 0) {
                        requestAnimationFrame(fadeOut);
                    } else {
                        this.scene.remove(shadow);
                    }
                };
                fadeOut();
            }
        };
        animate();
    }
    
    startMoonbeamEffect(player) {
        // Create moonbeam spotlight
        const spotlight = new THREE.SpotLight(THEME.moonlight, 3, 10, Math.PI / 8, 0.5);
        spotlight.position.set(
            player.position.x,
            10,
            player.position.z
        );
        spotlight.target = player;
        this.scene.add(spotlight);
        
        // Remove after duration
        setTimeout(() => {
            this.scene.remove(spotlight);
        }, 1000);
    }
    
    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        
        const time = this.clock.getElapsedTime();
        
        // Fire animation
        this.fireParticles.forEach((flame, i) => {
            flame.mesh.position.y = flame.baseY + Math.sin(time * 8 + flame.phase) * 0.1;
            flame.mesh.scale.y = 1 + Math.sin(time * 10 + flame.phase) * 0.2;
            flame.mesh.material.opacity = 0.7 + Math.sin(time * 12 + flame.phase) * 0.3;
        });
        
        // Fire light flicker
        this.fireLight.intensity = 2 + Math.sin(time * 8) * 0.3 + Math.sin(time * 13) * 0.2;
        
        // Star twinkle
        if (this.isNight) {
            this.stars.forEach(star => {
                star.mesh.material.opacity = 0.5 + Math.sin(time * 2 + star.phase) * 0.3;
            });
        }
        
        // Player breathing animation
        this.players.forEach(player => {
            if (player.userData.isAlive) {
                const breath = Math.sin(time * 2 + player.userData.breathPhase) * 0.02;
                player.position.y = player.userData.baseY + breath;
                
                // Nervous shaking
                if (player.userData.isNervous) {
                    player.position.x += (Math.random() - 0.5) * 0.02;
                    player.position.z += (Math.random() - 0.5) * 0.02;
                }
            }
        });
        
        // Clean up expired hints
        this.hints = this.hints.filter(hint => {
            return (time - hint.startTime) < hint.duration;
        });
        
        this.renderer.render(this.scene, this.camera);
    }
    
    async fetchVillageData() {
        try {
            const response = await fetch(`/api/village/${this.raumCode}`);
            const data = await response.json();
            
            if (data.players) {
                this.updatePlayers(data.players);
            }
            
            if (data.phase) {
                const isNight = data.phase.includes('nacht') || 
                               data.phase.includes('werwolf') ||
                               data.phase.includes('seherin') ||
                               data.phase.includes('hexe');
                this.setTimeOfDay(isNight);
            }
        } catch (error) {
            console.error('Failed to fetch village data:', error);
        }
    }
    
    onResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight || 400;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        window.removeEventListener('resize', this.onResize);
        
        // Dispose Three.js resources
        this.scene.traverse(object => {
            if (object.geometry) object.geometry.dispose();
            if (object.material) {
                if (Array.isArray(object.material)) {
                    object.material.forEach(m => m.dispose());
                } else {
                    object.material.dispose();
                }
            }
        });
        
        this.renderer.dispose();
        this.container.removeChild(this.renderer.domElement);
    }
}

// Export for global use
window.Village3D = Village3D;

export { Village3D };
