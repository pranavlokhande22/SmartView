(function() {
  'use strict';

  // Check for reduced motion preference
  function prefersReducedMotion() {
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  }

  // Enhanced Reveal Animation with 3D effects
  function setupRevealOnce() {
    const elements = [].slice.call(document.querySelectorAll('.reveal'));
    if (elements.length === 0) return;

    if (prefersReducedMotion()) {
      elements.forEach(el => el.classList.add('revealed'));
      return;
    }

    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    elements.forEach(el => io.observe(el));
  }

  // 3D Pipeline Timeline Animation
  function setupPipelineTimeline() {
    const wrap = document.getElementById('pipeline-timeline');
    if (!wrap) return;

    const bar = wrap.querySelector('.tl-bar');
    const dot = wrap.querySelector('.tl-dot');
    const steps = [].slice.call(wrap.querySelectorAll('.tl-step'));
    const caption = document.getElementById('tl-caption');
    const startBtn = document.getElementById('start-demo');
    let idx = 0;
    let timer = null;

    function setProgress(i) {
      const pct = (i / (steps.length - 1)) * 100;
      if (bar) bar.style.width = pct + '%';
      if (dot) dot.style.left = pct + '%';
      
      steps.forEach((s, k) => {
        s.classList.toggle('active', k <= i);
        if (k === i) {
          s.style.transform = 'translateY(-10px) scale(1.1)';
        } else if (k < i) {
          s.style.transform = 'scale(1)';
        }
      });
      
      if (caption && steps[i]) {
        caption.textContent = steps[i].getAttribute('data-title') + ' â€” ' + 
                             steps[i].getAttribute('data-desc');
      }
    }

    function play() {
      clearInterval(timer);
      idx = 0;
      setProgress(0);
      if (prefersReducedMotion()) return;

      timer = setInterval(() => {
        idx++;
        if (idx >= steps.length) {
          clearInterval(timer);
          return;
        }
        setProgress(idx);
      }, 1000);
    }

    if (startBtn) {
      startBtn.addEventListener('click', play);
    }

    // Auto-play when visible
    const autoIo = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          play();
          autoIo.disconnect();
        }
      });
    }, { threshold: 0.4 });

    autoIo.observe(wrap);
  }

  // 3D Parallax Effect on Mouse Move
  function setup3DParallax() {
    const cards = [].slice.call(document.querySelectorAll('.feature-card, .review-card, .pipeline .step'));
    
    if (prefersReducedMotion() || cards.length === 0) return;

    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const rotateX = (y - centerY) / 10;
        const rotateY = (centerX - x) / 10;
        
        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px)`;
      });
      
      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
      });
    });
  }

  // Animated Counter for Stats
  function setupCounters() {
    const counters = [].slice.call(document.querySelectorAll('.stat-number'));
    
    counters.forEach(counter => {
      const target = parseInt(counter.getAttribute('data-target') || counter.textContent);
      const duration = 2000;
      const step = target / (duration / 16);
      let current = 0;
      
      const io = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const timer = setInterval(() => {
              current += step;
              if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
              } else {
                counter.textContent = Math.floor(current);
              }
            }, 16);
            io.disconnect();
          }
        });
      }, { threshold: 0.5 });
      
      io.observe(counter);
    });
  }

  // Floating Animation for Hero Elements
  function setupFloatingElements() {
    const floatingElements = [].slice.call(document.querySelectorAll('.feature-icon'));
    
    if (prefersReducedMotion()) return;
    
    floatingElements.forEach((el, index) => {
      el.style.animation = `bounce 2s ease-in-out ${index * 0.2}s infinite`;
    });
  }

  // Gradient Animation Background
  function setupGradientAnimation() {
    const heroSection = document.querySelector('.hero');
    if (!heroSection || prefersReducedMotion()) return;
    
    heroSection.style.backgroundSize = '400% 400%';
    heroSection.style.animation = 'gradientShift 15s ease infinite';
  }

  // Glow Effect on Hover for Buttons
  function setupButtonGlow() {
    const buttons = [].slice.call(document.querySelectorAll('.cta-button, .q-btn, button'));
    
    buttons.forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        btn.style.setProperty('--mouse-x', x + 'px');
        btn.style.setProperty('--mouse-y', y + 'px');
      });
    });
  }

  // Scroll Progress Bar
  function setupScrollProgress() {
    const progressBar = document.createElement('div');
    progressBar.className = 'scroll-progress-bar';
    document.body.appendChild(progressBar);
    
    if (prefersReducedMotion()) return;
    
    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollPercent = (scrollTop / docHeight) * 100;
      progressBar.style.width = scrollPercent + '%';
    });
  }

  // Stagger Animation for List Items
  function setupStaggerAnimation() {
    const lists = [].slice.call(document.querySelectorAll('.footer-link, .review-row'));
    
    if (prefersReducedMotion()) return;
    
    lists.forEach((item, index) => {
      item.style.animation = `slideInLeft 0.6s ease-out ${index * 0.1}s both`;
    });
  }

  // Pulse Animation for Important Elements
  function setupPulseAnimation() {
    const importantElements = [].slice.call(document.querySelectorAll('.stat-card, .panel'));
    
    if (prefersReducedMotion()) return;
    
    importantElements.forEach(el => {
      el.addEventListener('mouseenter', () => {
        el.style.animation = 'pulse 1s ease-in-out';
      });
    });
  }

  // Text Shimmer Effect
  function setupShimmerEffect() {
    const headings = [].slice.call(document.querySelectorAll('h1, h2, h3, .text-h5, .text-h6'));
    
    if (prefersReducedMotion()) return;
    
    headings.forEach(heading => {
      heading.classList.add('shimmer-text');
    });
  }

  // Smooth Scroll
  function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  // Mouse Cursor Tracker
  function setupCursorTracker() {
    if (prefersReducedMotion()) return;
    
    const cursor = document.createElement('div');
    cursor.className = 'custom-cursor';
    document.body.appendChild(cursor);
    
    document.addEventListener('mousemove', (e) => {
      cursor.style.left = e.clientX + 'px';
      cursor.style.top = e.clientY + 'px';
    });
  }

  // Lottie Integration
  function setupLottieHooks() {
    const els = [].slice.call(document.querySelectorAll('[data-lottie]'));
    if (!els.length || !window.lottie) return;

    els.forEach(el => {
      try {
        const path = el.getAttribute('data-lottie');
        window.lottie.loadAnimation({
          container: el,
          renderer: 'svg',
          loop: true,
          autoplay: true,
          path: path
        });
      } catch (_) {
        // Ignore errors
      }
    });
  }

  // Initialize all animations
  function init() {
    setupRevealOnce();
    setupPipelineTimeline();
    setup3DParallax();
    setupCounters();
    setupFloatingElements();
    setupGradientAnimation();
    setupButtonGlow();
    setupScrollProgress();
    setupStaggerAnimation();
    setupPulseAnimation();
    setupShimmerEffect();
    setupSmoothScroll();
    setupCursorTracker();
    setupLottieHooks();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();