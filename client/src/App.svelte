<script>
  import { onMount, onDestroy } from 'svelte';
  import { daySummary } from './lib/stores';
  import { sessionStore } from './lib/sessionStore';
  import { get, post } from './lib/api';
  
  // Sub-views & Components
  import Analytics from './lib/Analytics.svelte';
  import SleepLog from './lib/SleepLog.svelte';
  import DataLogs from './lib/DataLogs.svelte';
  import BiologicalState from './lib/BiologicalState.svelte';
  import ActiveHUD from './lib/ActiveHUD.svelte';
  // --- State ---
  let today = new Date().toISOString().split('T')[0];
  let todaySessions = []; 
  let todaySleep = null;
  let todayIntake = null; // <-- ADD THIS
  let liveScore = 0;
  let extendedLiveScore = 0; // <-- ADD THIS
  let currentView = 'dashboard'; 
  
  // Dashboard UI State
  let hoveredItem = null;
  let outputMode = 'volume'; // 'volume' | 'state'
  let rightColMode = 'history'; // 'history' | 'queue'
  
  // HUD & Telemetry State
  let isHudVisible = true;
  let now = new Date();
  let tickerInterval;
  // Modals
  let showStartModal = false;
  let showEndModal = false;
  let showDetailModal = false;
  let showManualModal = false;
  let showRestModal = false; 
  let selectedSession = null;
  // --- Task Queue Data ---
  let tasks = [];
  let pendingTaskId = null; 
  let quickTask = {
      domain: "Work", project_name: "", activity_description: "", work_type: "Deep"
  };
  // --- Data Models ---
  let newSession = {
    domain: "Work", project_name: "", activity_description: "", work_type: "Deep", planned_duration_min: 90,
    energy_before: 7, stress_before: 3, resistance_before: 2
  };
  let restActivity = ""; 
  let endSessionData = {
    completion_status: "Completed", progress_rating: 4, quality_rating: 4, focus_quality: 4,
    moves_main_goal: true, evidence_note: "", energy_after: 7, stress_after: 3, feel_tag: "",
    work_type: "Deep"
  };
  let manualSession = {
    start_time: new Date(Date.now() - 3600000).toISOString().slice(0, 16),
    end_time: new Date().toISOString().slice(0, 16),
    domain: "Work", project_name: "", activity_description: "", work_type: "Deep",
    energy_before: 7, stress_before: 3, resistance_before: 2,
    completion_status: "Completed", progress_rating: 4, quality_rating: 4, focus_quality: 4,
    moves_main_goal: true, evidence_note: "",
    energy_after: 7, stress_after: 3, feel_tag: "neutral"
  };
  // --- Computed Metrics ---
  $: lastCompleted = todaySessions.find(s => s.outcome && s.after);
  $: currentStress = lastCompleted?.after?.stress ?? '-';
  $: currentEnergy = lastCompleted?.after?.energy ?? '-';
  $: lastFocus = lastCompleted?.outcome?.focus_quality ?? '-';
  $: topTags = getTopTags(todaySessions);
  
  // Intake calculations (same as DataLogs)
  $: intakePoints = calculateIntakePoints(todayIntake);
  $: extendedLiveScore = Math.min(100, liveScore + intakePoints);
  // Active Session Telemetry
  $: activeDurationSeconds = $sessionStore.active ? Math.floor((now - new Date($sessionStore.active.start_time)) / 1000) : 0;
  
  // System Load Calculation
  $: systemLoad = calculateSystemLoad(todaySessions);

  // Update endSessionData work type when modal opens
  $: if (showEndModal && $sessionStore.active) {
    endSessionData.work_type = $sessionStore.active.context.work_type;
  }

  // Work type suggestion state
  let workTypeSuggestion = null;
  let suggestingWorkType = false;
  let hasAutoAppliedSuggestion = false;
  let userChangedWorkType = false;
  let initialWorkType = "Deep"; // Default value
  function calculateSystemLoad(sessions) {
      // 4 hours of Deep Work (240m) = 100% Load
      let loadMinutes = 0;
      sessions.forEach(s => {
          if (!s.outcome) return;
          
          const duration = s.duration_minutes || 0;
          
          if (s.context.work_type === 'Deep') {
              loadMinutes += duration * 1.0;
          } else if (s.context.work_type === 'Shallow') {
              loadMinutes += duration * 0.3;
          } else if (s.context.work_type === 'Recovery') {
              loadMinutes -= duration * 0.5; // Cooling effect
          }
      });
      // Clamp between 0 and 100
      return Math.max(0, Math.min(100, Math.round((loadMinutes / 240) * 100)));
  }
  function getTopTags(sessions) {
      const counts = {};
      sessions.forEach(s => {
          if (s.after?.feel_tag) {
              const tag = s.after.feel_tag.toLowerCase().trim();
              if (tag) counts[tag] = (counts[tag] || 0) + 1;
          }
      });
      return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([tag]) => tag);
  }
  // Intake point calculation (same as DataLogs)
  function calculateIntakePoints(intake) {
      if (!intake) return 0;
      let points = 0;
      
      // Water: 1 point per 2 glasses, max 5 points (10 glasses)
      points += Math.min(5, Math.floor(intake.water_count / 2));
      
      // Meals: 5 points per meal logged, max 15 points (3 meals)
      const mealsLogged = [intake.breakfast_time, intake.lunch_time, intake.dinner_time].filter(Boolean).length;
      points += mealsLogged * 5;
      
      // Cap intake points at 20 (20% of total score)
      return Math.min(20, points);
  }
  // --- Graphic Helpers ---
  const domainColors = {
    'Work': 'bg-emerald-500', 'Personal Project': 'bg-violet-500', 'College': 'bg-blue-500',
    'Learning': 'bg-cyan-500', 'Health': 'bg-rose-500', 'Admin': 'bg-zinc-500', 'Relationships': 'bg-amber-500'
  };
  const typeOpacity = {
    'Deep': 'opacity-100', 
    'Shallow': 'opacity-60', 
    'Maintenance': 'opacity-30',
    'Recovery': 'opacity-90' 
  };
  function getSessionScore(s) {
    if (!s.outcome) return 0;
    const score = (s.outcome.progress_rating * 2) + (s.outcome.focus_quality * 1.5) + (s.outcome.quality_rating * 1);
    return Math.min(100, (score / 22.5) * 100);
  }
  function getPosition(session) {
    const start = new Date(session.start_time);
    const startMins = (start.getHours() * 60) + start.getMinutes();
    
    let duration = session.duration_minutes;
    // Dynamic Growth: If session is active, calculate duration relative to 'now'
    if (!duration && !session.is_finished) {
        duration = Math.floor((now - start) / 60000);
    }
    
    const left = (startMins / 1440) * 100;
    const width = (duration / 1440) * 100;
    return { left: `${left}%`, width: `${Math.max(0.5, width)}%` };
  }
  function getSleepPosition(sleep) {
      if (!sleep) return null;

      // Create date objects for sleep times
      const sStart = new Date(sleep.sleep_start);
      const sEnd = new Date(sleep.sleep_end);

      // Create date objects for chart day boundaries
      const chartDate = new Date(today);
      const dayStart = new Date(chartDate);
      dayStart.setHours(0, 0, 0, 0);

      const dayEnd = new Date(chartDate);
      dayEnd.setHours(23, 59, 59, 999);

      // Calculate overlap with chart day
      const overlapStart = sStart < dayStart ? dayStart : sStart;
      const overlapEnd = sEnd > dayEnd ? dayEnd : sEnd;

      // Check if there's any overlap
      if (overlapEnd <= overlapStart) return null;

      // Calculate position and width
      const startMins = (overlapStart.getHours() * 60) + overlapStart.getMinutes();
      const durationMins = (overlapEnd.getTime() - overlapStart.getTime()) / 1000 / 60;

      const left = (startMins / 1440) * 100;
      const width = (durationMins / 1440) * 100;

      return { left: `${left}%`, width: `${width}%` };
  }
  function formatTime(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  function formatDurationHM(mins) {
      if (!mins) return '0h 0m';
      const h = Math.floor(mins / 60);
      const m = mins % 60;
      return `${h}h ${m}m`;
  }
  
  function formatTicker(totalSeconds) {
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;
        return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  // --- Continuity Logic ---
  function prefillBioState() {
      if (lastCompleted && lastCompleted.after) {
          newSession.energy_before = lastCompleted.after.energy;
          newSession.stress_before = lastCompleted.after.stress;
      }
  }
  // --- Lifecycle & Actions ---
  onMount(() => {
      refreshData();
      loadTasks();
      
      tickerInterval = setInterval(() => {
          now = new Date();
      }, 1000);
  });
  
  onDestroy(() => {
      clearInterval(tickerInterval);
  });
  async function refreshData() {
    await daySummary.load(today);
    await sessionStore.checkActive();
    if ($sessionStore.active) {
        isHudVisible = true;
    }
    
    try {
        const [sessions, sleep, scoreData, intakeData] = await Promise.all([
            get('/sessions', { start_date: today, end_date: today }),
            get(`/sleep?date=${today}`),
            get('/analytics/score'),
            get(`/intake?date=${today}`)
        ]);
        todaySessions = sessions.sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime());
        todaySleep = sleep;
        todayIntake = intakeData;
        liveScore = scoreData.score || 0;
    } catch (e) { console.error(e); }
  }
  // --- Task Logic ---
  async function loadTasks() {
      try { tasks = await get('/tasks'); } catch(e) { console.error("Failed to load tasks", e); }
  }
  async function handleQuickCapture() {
      if(!quickTask.project_name) return;
      await post('/tasks', quickTask);
      quickTask.project_name = "";
      quickTask.activity_description = "";
      loadTasks();
  }
  function activateTask(task) {
      prefillBioState();
      newSession.domain = task.domain;
      newSession.project_name = task.project_name;
      newSession.activity_description = task.activity_description;
      newSession.work_type = task.work_type;
      
      pendingTaskId = task.id;
      showStartModal = true;
  }
  
  async function deleteTask(id) {
       await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
       loadTasks();
  }
  async function handleStart() {
    await sessionStore.start(newSession);
    showStartModal = false;
    isHudVisible = true; 
    
    if (pendingTaskId) {
        await deleteTask(pendingTaskId);
        pendingTaskId = null;
    }
    
    refreshData();
  }
  // Recovery Protocol
  async function handleRestStart() {
    prefillBioState();
    newSession.domain = "Health";
    newSession.project_name = "System Recovery";
    newSession.activity_description = restActivity;
    newSession.work_type = "Recovery";
    
    if(!lastCompleted) {
        newSession.energy_before = 3;
        newSession.stress_before = 7;
    }
    await sessionStore.start(newSession);
    showRestModal = false;
    isHudVisible = true;
    refreshData();
  }
  async function confirmEndSession() {
    if (!$sessionStore.active) return;
    if (!endSessionData.feel_tag.trim()) endSessionData.feel_tag = "neutral";

    // First end the session
    await sessionStore.stop($sessionStore.active.id, endSessionData);

    // Update work type if it changed from the original
    const originalWorkType = $sessionStore.active.context.work_type;
    if (endSessionData.work_type && endSessionData.work_type !== originalWorkType) {
      try {
        await fetch(`/api/sessions/${$sessionStore.active.id}/work-type`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ work_type: endSessionData.work_type })
        });
      } catch (e) {
        console.error("Failed to update work type:", e);
      }
    }

    showEndModal = false;
    isHudVisible = false;
    endSessionData.evidence_note = "";
    endSessionData.feel_tag = "";
    endSessionData.work_type = "Deep"; // Reset to default
    refreshData();
  }
  async function handleDelete(id) {
      if(!confirm("Permanently delete this record?")) return;
      await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
      showDetailModal = false;
      selectedSession = null;
      refreshData();
  }
  async function handleManualSubmit() {
      const payload = {
          ...manualSession,
          start_time: manualSession.start_time,
          end_time: manualSession.end_time
      };
      await post('/sessions/manual', payload);
      showManualModal = false;
      refreshData();
  }
  function openDetail(session) {
      selectedSession = session;
      showDetailModal = true;
  }
  // GLOBAL HOTKEYS
  function handleGlobalKeydown(e) {
      if (e.ctrlKey && e.code === 'Space') {
          e.preventDefault();
          if ($sessionStore.active) {
              isHudVisible = true;
          }
      }
  }

  async function suggestWorkType() {
    if (!newSession.activity_description.trim()) return;

    // Don't suggest if we've already auto-applied or user manually changed work type
    if (hasAutoAppliedSuggestion || userChangedWorkType) return;

    // Don't suggest if we already have a suggestion for the same text
    if (workTypeSuggestion && workTypeSuggestion.lastActivity === newSession.activity_description) {
      return;
    }

    suggestingWorkType = true;

    try {
      const response = await fetch('/api/suggest-work-type', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          activity_description: newSession.activity_description
        })
      });

      if (response.ok) {
        const data = await response.json();

        // Only update suggestion if conditions still hold (they might have changed during fetch)
        if (!hasAutoAppliedSuggestion && !userChangedWorkType) {
          // Store the activity description that this suggestion is for
          data.lastActivity = newSession.activity_description;
          workTypeSuggestion = data;

          // Auto-apply suggestion only if:
          // 1. Confidence is high AND score > 0.7
          // 2. We haven't auto-applied before in this session
          // 3. User hasn't manually changed the work type
          if (data.confidence === 'high' && data.score > 0.7) {
            newSession.work_type = data.suggested_work_type;
            hasAutoAppliedSuggestion = true;
          }
        }
      }
    } catch (e) {
      console.error("Failed to get work type suggestion:", e);
    } finally {
      suggestingWorkType = false;
    }
  }

  // Track when user manually changes work type
  $: if (showStartModal && newSession.work_type !== initialWorkType && !hasAutoAppliedSuggestion) {
    userChangedWorkType = true;
  }

  // Reset suggestion state when modal opens/closes
  $: if (showStartModal) {
    // Set initial work type when modal opens
    initialWorkType = newSession.work_type;
  } else {
    // Reset when modal closes
    hasAutoAppliedSuggestion = false;
    userChangedWorkType = false;
    workTypeSuggestion = null;
    initialWorkType = "Deep";
  }

  // Auto-suggest when activity description changes (debounced)
  let suggestionTimeout;
  $: {
    // Only suggest if:
    // 1. We have enough text (> 10 chars)
    // 2. We haven't auto-applied a suggestion yet
    // 3. User hasn't manually changed work type
    if (newSession.activity_description && newSession.activity_description.length > 10 &&
        !hasAutoAppliedSuggestion && !userChangedWorkType) {

      // Clear any existing timeout
      if (suggestionTimeout) {
        clearTimeout(suggestionTimeout);
        suggestionTimeout = null;
      }

      // Set new timeout for suggestion
      suggestionTimeout = setTimeout(() => {
        // Double-check conditions haven't changed during the timeout
        if (!hasAutoAppliedSuggestion && !userChangedWorkType) {
          suggestWorkType();
        }
      }, 1000);
    } else {
      // If conditions aren't met, clear any pending timeout
      if (suggestionTimeout) {
        clearTimeout(suggestionTimeout);
        suggestionTimeout = null;
      }
      // Also clear the suggestion if text is too short or empty
      if (!newSession.activity_description || newSession.activity_description.length <= 10) {
        workTypeSuggestion = null;
      }
    }
  }
</script>
<svelte:window on:keydown={handleGlobalKeydown} />
<main class="h-screen w-screen bg-[#09090b] text-zinc-300 font-sans selection:bg-emerald-500/30 flex flex-col overflow-hidden">
  
  {#if $sessionStore.active && isHudVisible}
      <ActiveHUD 
          session={$sessionStore.active} 
          on:minimize={() => isHudVisible = false}
          on:end={() => { isHudVisible = false; showEndModal = true; }}
      />
  {/if}
  <header class="h-14 flex-none border-b border-zinc-800/50 bg-zinc-900/20 backdrop-blur-sm z-40">
    <div class="w-full px-6 h-full flex justify-between items-center">
        <div class="flex items-center gap-6">
            <div class="flex items-center gap-3">
                <div class="w-3 h-3 bg-emerald-500 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                <span class="font-bold tracking-tight text-zinc-100">ICARUS</span>
            </div>
            <nav class="flex gap-1 bg-zinc-900/50 p-1 rounded-lg border border-zinc-800">
                {#each ['dashboard', 'analytics', 'logs', 'sleep'] as tab}
                    <button 
                        on:click={() => currentView = tab}
                        class="px-3 py-1 text-xs font-medium rounded-md capitalize transition-all {currentView === tab ? 'bg-zinc-700 text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-300'}"
                    >
                        {tab}
                    </button>
                {/each}
            </nav>
        </div>
        
        <div class="flex items-center gap-6">
            <div class="flex flex-col items-end">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">System Temp</span>
                    <span class="font-mono text-xs font-bold {systemLoad > 80 ? 'text-red-500' : systemLoad > 40 ? 'text-amber-500' : 'text-emerald-500'}">
                        {systemLoad}%
                    </span>
                </div>
                <div class="w-24 h-1 bg-zinc-800 rounded-full overflow-hidden">
                    <div 
                        class="h-full transition-all duration-500 {systemLoad > 80 ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' : systemLoad > 40 ? 'bg-amber-500' : 'bg-emerald-500'}" 
                        style="width: {systemLoad}%">
                    </div>
                </div>
            </div>
            <div class="font-mono text-xs text-zinc-600 uppercase tracking-widest">{today}</div>
        </div>
    </div>
  </header>
  <div class="flex-1 overflow-hidden relative">
    
    {#if currentView === 'dashboard'}
        <div class="h-full w-full p-6">
            <div class="grid grid-cols-12 gap-8 h-full">
                
                <div class="col-span-12 lg:col-span-8 flex flex-col gap-8 h-full">
                    
                    <div class="flex-1 min-h-0 bg-[#0c0c0e] border border-zinc-800 rounded-xl p-0 relative overflow-hidden flex flex-col shadow-inner group/chart">
                        
                        <div class="absolute top-4 left-6 right-6 flex justify-between items-start z-20 pointer-events-none">
                            <div class="flex flex-col">
                                <h3 class="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">Temporal Horizon</h3>
                                <div class="flex items-center gap-2 mt-1">
                                    <span class="text-[9px] text-zinc-600 font-mono">Top: Output</span>
                                    <span class="text-[9px] text-zinc-700 font-mono">|</span>
                                    <span class="text-[9px] text-zinc-600 font-mono">Bottom: Bio-Cost & Sleep</span>
                                </div>
                            </div>
                            <div class="absolute left-1/2 -translate-x-1/2 top-0 pointer-events-none z-[100]">
                                {#if hoveredItem}
                                    <div class="bg-zinc-900/95 backdrop-blur-md border border-zinc-700 px-4 py-2 rounded-lg shadow-2xl flex gap-6 animate-in fade-in zoom-in-95 duration-100 mt-4">
                                        {#if hoveredItem.type === 'session'}
                                            {@const s = hoveredItem.data}
                                            {@const score = getSessionScore(s)}
                                            <div class="flex flex-col">
                                                <span class="text-[9px] text-zinc-500 uppercase font-bold">Project</span>
                                                <span class="text-xs font-bold text-white whitespace-nowrap">{s.context.project_name}</span>
                                            </div>
                                            <div class="flex flex-col">
                                                <span class="text-[9px] text-zinc-500 uppercase font-bold">Time</span>
                                                <span class="text-xs font-mono text-zinc-300">{formatTime(s.start_time)}</span>
                                            </div>
                                            {#if s.outcome}
                                                <div class="flex flex-col">
                                                    <span class="text-[9px] text-zinc-500 uppercase font-bold">Score</span>
                                                    <span class="text-xs font-mono text-emerald-400">{Math.round(score)}</span>
                                                </div>
                                            {/if}
                                        {:else if hoveredItem.type === 'sleep'}
                                            {@const sl = hoveredItem.data}
                                            <div class="flex flex-col">
                                                <span class="text-[9px] text-zinc-500 uppercase font-bold">Bio-Input</span>
                                                <span class="text-xs font-bold text-violet-300">Sleep Protocol</span>
                                            </div>
                                            <div class="flex flex-col">
                                                <span class="text-[9px] text-zinc-500 uppercase font-bold">Quality</span>
                                                <span class="text-xs font-mono text-white">{sl.sleep_quality}/5</span>
                                            </div>
                                        {/if}
                                    </div>
                                {:else}
                                    <div class="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 px-4 py-1.5 rounded-full flex gap-3 mt-4">
                                        <span class="text-[10px] text-zinc-500 font-bold uppercase tracking-wider pt-0.5">Daily Index</span>
                                        <span class="text-sm font-mono font-bold {extendedLiveScore >= 80 ? 'text-emerald-400' : extendedLiveScore >= 50 ? 'text-violet-400' : 'text-red-400'}">
                                            {extendedLiveScore}
                                        </span>
                                        {#if intakePoints > 0}
                                            <span class="text-[9px] text-cyan-400 font-bold" title="Includes intake points">+{intakePoints} intake</span>
                                        {/if}
                                    </div>
                                {/if}
                            </div>
                            <div class="pointer-events-auto flex gap-2">
                                {#if $sessionStore.active}
                                    <button on:click={() => isHudVisible = true} class="flex items-center gap-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-3 py-1.5 rounded-full text-[10px] uppercase font-bold hover:bg-emerald-500/20 transition-all shadow-[0_0_15px_rgba(16,185,129,0.1)]">
                                        <div class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></div>
                                        <span class="font-mono">{formatTicker(activeDurationSeconds)}</span>
                                    </button>
                                {:else}
                                    <button on:click={() => showRestModal = true} class="bg-cyan-900/30 text-cyan-400 border border-cyan-800/50 px-3 py-1.5 rounded text-[10px] uppercase font-bold hover:bg-cyan-900/50 transition-all backdrop-blur-md flex items-center gap-2">
                                        <span>❄️</span> Cool Down
                                    </button>
                                    <button on:click={() => { pendingTaskId = null; prefillBioState(); showStartModal = true; }} class="bg-zinc-800/50 text-zinc-400 border border-zinc-700/50 px-3 py-1.5 rounded text-[10px] uppercase font-bold hover:bg-zinc-700 hover:text-white transition-all backdrop-blur-md">
                                        + Initialize
                                    </button>
                                {/if}
                            </div>
                        </div>
                        <div class="relative flex-1 w-full mt-4">
                            <div class="absolute top-[70%] left-0 right-0 h-px bg-zinc-700 z-10"></div>
                            
                            <div class="absolute inset-0 pointer-events-none">
                                {#each [0, 4, 8, 12, 16, 20, 24] as hour}
                                    {@const position = (hour / 24) * 100}
                                    <div
                                        class="absolute top-0 bottom-0 border-r border-zinc-800/30"
                                        style="left: {position}%;"
                                    >
                                        <span class="absolute bottom-2 -right-3 text-[9px] text-zinc-700 font-mono">{hour.toString().padStart(2, '0')}:00</span>
                                    </div>
                                {/each}
                            </div>
                            <div class="absolute inset-0 mx-[2px]"> 
                                {#if todaySleep}
                                    {@const pos = getSleepPosition(todaySleep)}
                                    {#if pos}
                                        <div 
                                            class="absolute top-[70%] bottom-0 z-0 bg-violet-500/10 border-x border-violet-500/20 hover:bg-violet-500/20 transition-colors cursor-crosshair"
                                            style="left: {pos.left}; width: {pos.width};"
                                            on:mouseenter={() => hoveredItem = { type: 'sleep', data: todaySleep }}
                                            on:mouseleave={() => hoveredItem = null}
                                        >
                                            <div class="absolute top-0 left-0 right-0 h-0.5 bg-violet-500/50"></div>
                                        </div>
                                    {/if}
                                {/if}
                                {#each todaySessions as s}
                                    {@const pos = getPosition(s)}
                                    {@const score = getSessionScore(s)}
                                    {@const color = domainColors[s.context.domain] || 'bg-zinc-500'}
                                    {@const opacity = typeOpacity[s.context.work_type] || 'opacity-100'}
                                    
                                    {#if s.outcome}
                                        {@const stress = s.after?.stress || 0}
                                        {@const stressHeight = (stress / 10) * 25}
                                        {@const stressColor = stress > 7 ? 'bg-red-500' : stress > 4 ? 'bg-orange-500/80' : 'bg-zinc-700/50'}
                                        <div class="absolute top-[70%] rounded-b-[2px] {stressColor} transition-all border-x border-white/5 pointer-events-none z-10 mix-blend-hard-light" style="left: {pos.left}; width: {pos.width}; height: {stressHeight}%;"></div>
                                    {/if}
                                    <div
                                        class="absolute bottom-[30%] group transition-all duration-300 hover:z-50 cursor-pointer z-20"
                                        style="left: {pos.left}; width: {pos.width}; height: {s.outcome ? (score * 0.5) : 30}%;"
                                        on:mouseenter={() => hoveredItem = { type: 'session', data: s }}
                                        on:mouseleave={() => hoveredItem = null}
                                        on:click={() => openDetail(s)}
                                    >
                                        <div class="w-full h-full rounded-t-[2px] {color} {opacity} border-t border-x border-white/10 bg-gradient-to-b from-white/10 to-transparent backdrop-blur-[1px] hover:brightness-125 shadow-[0_-4px_15px_rgba(0,0,0,0.3)]"></div>
                                    </div>
                                {/each}
                                {#if $sessionStore.active}
                                    {@const activeS = $sessionStore.active}
                                    {@const pos = getPosition(activeS)}
                                    <div class="absolute bottom-[30%] z-20 group transition-all duration-1000 ease-linear" style="left: {pos.left}; width: {pos.width}; height: 25%;">
                                        <div class="w-full h-full rounded-t-[2px] border-t border-x border-emerald-500/30 bg-[repeating-linear-gradient(45deg,rgba(16,185,129,0.1),rgba(16,185,129,0.1)_10px,rgba(16,185,129,0.05)_10px,rgba(16,185,129,0.05)_20px)] animate-pulse"></div>
                                        <div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-emerald-500 text-black text-[9px] font-bold px-1.5 py-0.5 rounded shadow-[0_0_10px_rgba(16,185,129,0.4)] tracking-wider">LIVE</div>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    </div>
                    <div class="h-72 flex-none grid grid-cols-2 gap-8">
                        <!-- BiologicalState component - update it to show intake as well -->
                        <BiologicalState sleepData={todaySleep} intakeData={todayIntake} />
                        <div class="bg-zinc-900/40 border border-zinc-800/50 rounded-xl p-5 relative overflow-hidden flex flex-col">
                            <div class="flex justify-between items-start mb-4">
                                <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mt-1">
                                    {outputMode === 'volume' ? 'Production Volume' : 'Current State'}
                                </h3>
                                
                                <div class="bg-black border border-zinc-800 rounded-lg p-0.5 flex">
                                    <button on:click={() => outputMode = 'volume'} class="px-2 py-1 rounded-md text-[10px] uppercase font-bold transition-all {outputMode === 'volume' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-600 hover:text-zinc-400'}">Vol</button>
                                    <button on:click={() => outputMode = 'state'} class="px-2 py-1 rounded-md text-[10px] uppercase font-bold transition-all {outputMode === 'state' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-600 hover:text-zinc-400'}">State</button>
                                </div>
                            </div>
                            {#if outputMode === 'volume'}
                                {#if $daySummary}
                                    <div class="flex items-end gap-2 mb-4 animate-in fade-in slide-in-from-right-4 duration-300">
                                        <span class="text-4xl font-light text-white">{$daySummary.deep_minutes}</span>
                                        <span class="text-sm text-zinc-500 mb-1">deep minutes</span>
                                    </div>
                                    <div class="space-y-1.5 overflow-y-auto max-h-[100px] pr-2 scrollbar-thin scrollbar-thumb-zinc-800 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                        {#if $daySummary.minutes_by_domain}
                                            {#each Object.entries($daySummary.minutes_by_domain) as [domain, mins]}
                                                <div class="flex items-center gap-2 text-xs">
                                                    <div class="w-2 h-2 rounded-full {domainColors[domain] || 'bg-zinc-500'}"></div>
                                                    <span class="text-zinc-400 flex-1 truncate">{domain}</span>
                                                    <span class="font-mono text-zinc-500">{mins}m</span>
                                                </div>
                                            {/each}
                                        {/if}
                                    </div>
                                {/if}
                            {:else}
                                <div class="flex flex-col justify-between h-full animate-in fade-in slide-in-from-left-4 duration-300">
                                    <div class="space-y-3">
                                        <div>
                                            <div class="flex justify-between text-[10px] uppercase text-zinc-500 font-bold mb-1"><span>Focus (Last)</span><span class="text-blue-400">{lastFocus}/5</span></div>
                                            {#if typeof lastFocus === 'number'}
                                            <div class="h-1.5 bg-zinc-800 rounded-full overflow-hidden"><div class="h-full bg-blue-500" style="width: {(lastFocus/5)*100}%"></div></div>
                                            {/if}
                                        </div>
                                        <div>
                                            <div class="flex justify-between text-[10px] uppercase text-zinc-500 font-bold mb-1"><span>Energy (Current)</span><span class="text-emerald-400">{currentEnergy}/10</span></div>
                                            {#if typeof currentEnergy === 'number'}
                                            <div class="h-1.5 bg-zinc-800 rounded-full overflow-hidden"><div class="h-full bg-emerald-500" style="width: {(currentEnergy/10)*100}%"></div></div>
                                            {/if}
                                        </div>
                                        <div>
                                            <div class="flex justify-between text-[10px] uppercase text-zinc-500 font-bold mb-1"><span>Stress (Current)</span><span class="text-rose-400">{currentStress}/10</span></div>
                                            {#if typeof currentStress === 'number'}
                                            <div class="h-1.5 bg-zinc-800 rounded-full overflow-hidden"><div class="h-full bg-rose-500" style="width: {(currentStress/10)*100}%"></div></div>
                                            {/if}
                                        </div>
                                    </div>
                                    <div class="mt-auto pt-2 border-t border-zinc-800/50">
                                        <div class="flex flex-wrap gap-2">
                                            {#if topTags.length > 0}
                                                {#each topTags as tag}<span class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-[10px] text-zinc-300 uppercase tracking-wider">{tag}</span>{/each}
                                            {:else}
                                                <span class="text-[10px] text-zinc-600 italic">No feelings recorded</span>
                                            {/if}
                                        </div>
                                    </div>
                                </div>
                            {/if}
                        </div>
                    </div>
                </div>
                <div class="col-span-12 lg:col-span-4 h-full min-h-0">
                    <div class="bg-zinc-900/40 border border-zinc-800/50 rounded-xl h-full flex flex-col relative overflow-hidden">
                        
                        <div class="p-4 border-b border-zinc-800/50 bg-zinc-900/20 flex-none flex justify-between items-center">
                            <div class="flex bg-black p-0.5 rounded-lg border border-zinc-800">
                                <button 
                                    on:click={() => rightColMode = 'history'}
                                    class="px-3 py-1 text-[10px] uppercase font-bold rounded-md transition-all {rightColMode === 'history' ? 'bg-zinc-800 text-white shadow' : 'text-zinc-600 hover:text-zinc-400'}"
                                >
                                    History
                                </button>
                                <button 
                                    on:click={() => { rightColMode = 'queue'; loadTasks(); }}
                                    class="px-3 py-1 text-[10px] uppercase font-bold rounded-md transition-all {rightColMode === 'queue' ? 'bg-zinc-800 text-white shadow' : 'text-zinc-600 hover:text-zinc-400'}"
                                >
                                    Queue
                                </button>
                            </div>
                            {#if rightColMode === 'history'}
                                <button on:click={() => showManualModal = true} class="text-zinc-500 hover:text-white transition-colors" title="Log past session">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                                </button>
                            {:else}
                                <span class="text-[10px] font-mono text-zinc-600">{tasks.length} PENDING</span>
                            {/if}
                        </div>
                        <div class="flex-1 overflow-y-auto p-0 scrollbar-thin scrollbar-thumb-zinc-800">
                            
                            {#if rightColMode === 'history'}
                                {#if todaySessions.length === 0}
                                    <div class="flex items-center justify-center h-32 text-zinc-700 text-sm italic">No records yet.</div>
                                {:else}
                                    <div class="divide-y divide-zinc-800/30">
                                        {#each todaySessions as s}
                                            <div class="p-5 hover:bg-zinc-800/20 transition-colors group relative cursor-pointer" on:mouseenter={() => hoveredItem = { type: 'session', data: s }} on:mouseleave={() => hoveredItem = null} on:click={() => openDetail(s)}>
                                                {#if !s.outcome}
                                                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500 animate-pulse"></div>
                                                {/if}
                                                <div class="flex justify-between items-start mb-2">
                                                    <span class="font-mono text-[10px] text-zinc-500 uppercase">{formatTime(s.start_time)}</span>
                                                    {#if s.outcome}
                                                        <div class="flex gap-2">
                                                            {#if s.context.work_type === 'Deep'}
                                                                <span class="text-[9px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 font-bold">DEEP</span>
                                                            {:else if s.context.work_type === 'Recovery'}
                                                                <span class="text-[9px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-bold">RECOVERY</span>
                                                            {/if}
                                                            <span class="text-[9px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono">R:{s.outcome.progress_rating}</span>
                                                        </div>
                                                    {/if}
                                                </div>
                                                <div class="font-bold text-base text-zinc-200 mb-1">{s.context.project_name}</div>
                                                <div class="text-xs text-zinc-500 truncate">{s.context.activity_description}</div>
                                            </div>
                                        {/each}
                                    </div>
                                {/if}
                            {:else}
                                <div class="p-4 space-y-4">
                                    <div class="bg-black/40 border border-zinc-800 rounded-lg p-3 space-y-3">
                                        <div class="flex gap-2">
                                            <input bind:value={quickTask.project_name} class="bg-zinc-900 border border-zinc-800 text-xs text-white px-2 py-1.5 rounded flex-1 outline-none focus:border-emerald-500/50" placeholder="Project name..." />
                                            <select bind:value={quickTask.domain} class="bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-400 px-1 rounded outline-none w-20">
                                                <option>Work</option><option>Personal Project</option><option>College</option><option>Learning</option><option>Admin</option><option>Health</option><option>Relationships</option>
                                            </select>
                                        </div>
                                        <div class="flex gap-2">
                                            <input bind:value={quickTask.activity_description} class="bg-zinc-900 border border-zinc-800 text-xs text-white px-2 py-1.5 rounded flex-1 outline-none focus:border-emerald-500/50" placeholder="Task description..." />
                                            <button on:click={handleQuickCapture} class="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 rounded text-xs font-bold transition-colors">+</button>
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        {#each tasks as task}
                                            <div class="group flex items-start gap-3 bg-zinc-900/30 border border-zinc-800/50 p-3 rounded-lg hover:border-emerald-500/30 transition-all cursor-pointer relative overflow-hidden" 
                                                 on:click={() => activateTask(task)}>
                                                <div class="absolute inset-0 bg-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                                <div class="mt-1 w-2 h-2 rounded-full flex-none {domainColors[task.domain] || 'bg-zinc-600'}"></div>
                                                <div class="flex-1 min-w-0 z-10">
                                                    <div class="flex justify-between items-center mb-0.5">
                                                        <span class="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">{task.project_name}</span>
                                                        <span class="text-[9px] text-zinc-600 font-mono bg-zinc-950 px-1.5 rounded">{task.work_type}</span>
                                                    </div>
                                                    <div class="text-sm text-zinc-300 group-hover:text-white transition-colors line-clamp-2">{task.activity_description}</div>
                                                </div>
                                                <button 
                                                    on:click|stopPropagation={() => deleteTask(task.id)}
                                                    class="opacity-0 group-hover:opacity-100 p-1 text-zinc-600 hover:text-red-500 transition-all z-20"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        {:else}
                                            <div class="text-center py-8 text-zinc-700 text-xs uppercase tracking-widest">Queue Empty</div>
                                        {/each}
                                    </div>
                                </div>
                            {/if}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    {:else if currentView === 'analytics'}
        <div class="h-full overflow-y-auto px-6 pb-20"><Analytics /></div>
    {:else if currentView === 'logs'}
        <div class="h-full w-full p-6 overflow-hidden"><DataLogs /></div>
    {:else if currentView === 'sleep'}
        <div class="h-full overflow-y-auto px-6 pb-20"><SleepLog /></div>
    {/if}
  </div>

  {#if showStartModal}
    <div class="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-xl w-full max-w-2xl shadow-2xl relative">
             <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-white">Initialize Session</h3>
                <button on:click={() => showStartModal = false} class="text-zinc-500 hover:text-white">✕</button>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Domain</label>
                    <select bind:value={newSession.domain} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none">
                        <option>Work</option><option>Personal Project</option><option>College</option><option>Learning</option><option>Admin</option><option>Health</option><option>Relationships</option>
                    </select>
                </div>
                <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Work Type</label>
                    <div class="space-y-2">
                        <select bind:value={newSession.work_type} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none">
                            <option>Deep</option><option>Shallow</option><option>Maintenance</option><option>Unknown</option>
                        </select>

                        {#if suggestingWorkType}
                            <div class="flex items-center gap-2 text-xs text-zinc-500">
                                <div class="w-3 h-3 border-2 border-zinc-600 border-t-emerald-500 rounded-full animate-spin"></div>
                                <span>Analyzing activity...</span>
                            </div>
                        {:else if workTypeSuggestion && !userChangedWorkType}
                            <div class="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <div class="flex justify-between items-center">
                                    <div class="flex items-center gap-2">
                                        <span class="text-xs font-bold uppercase text-zinc-400">AI Suggestion:</span>
                                        <span class="px-2 py-1 rounded text-xs font-bold {workTypeSuggestion.suggested_work_type === 'Deep' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : workTypeSuggestion.suggested_work_type === 'Shallow' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'}">
                                            {workTypeSuggestion.suggested_work_type}
                                        </span>
                                        <span class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                                            {workTypeSuggestion.confidence}
                                        </span>
                                    </div>
                                    <button
                                        on:click={() => newSession.work_type = workTypeSuggestion.suggested_work_type}
                                        class="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded font-bold transition-colors"
                                    >
                                        Apply
                                    </button>
                                </div>

                                {#if workTypeSuggestion.reasons && workTypeSuggestion.reasons.length > 0}
                                    <div class="text-xs text-zinc-500 space-y-1">
                                        {#each workTypeSuggestion.reasons as reason}
                                            <div class="flex items-start gap-2">
                                                <span class="text-zinc-600 mt-0.5">•</span>
                                                <span>{reason}</span>
                                            </div>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                </div>
                <div class="space-y-2 md:col-span-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Project</label>
                    <input bind:value={newSession.project_name} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none placeholder:text-zinc-700" placeholder="e.g. Backend Refactor" />
                </div>
                <div class="space-y-2 md:col-span-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Activity</label>
                    <input bind:value={newSession.activity_description} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none placeholder:text-zinc-700" placeholder="Specific task description..." />
                </div>
                <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Planned Min</label>
                    <input type="number" bind:value={newSession.planned_duration_min} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none" />
                </div>
                 <div class="md:col-span-2 grid grid-cols-3 gap-4 pt-4 border-t border-zinc-800">
                     <div class="space-y-2">
                        <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Energy</label>
                        <input type="number" min="1" max="10" bind:value={newSession.energy_before} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none" />
                    </div>
                     <div class="space-y-2">
                        <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Stress</label>
                        <input type="number" min="1" max="10" bind:value={newSession.stress_before} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none" />
                    </div>
                     <div class="space-y-2">
                        <label class="text-xs uppercase tracking-wider text-zinc-500 font-semibold">Resistance</label>
                        <input type="number" min="1" max="5" bind:value={newSession.resistance_before} class="w-full bg-black border border-zinc-800 rounded px-3 py-2.5 text-white focus:border-emerald-500 outline-none" />
                    </div>
                </div>
            </div>
            <div class="flex justify-end gap-4 pt-4 border-t border-zinc-800">
                <button on:click={() => showStartModal = false} class="px-6 py-2.5 rounded font-medium text-zinc-500 hover:text-white transition-colors">Cancel</button>
                <button on:click={handleStart} class="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-2.5 rounded font-bold transition-colors shadow-lg shadow-emerald-900/20">Engage</button>
            </div>
        </div>
    </div>
  {/if}

  {#if showRestModal}
    <div class="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-xl w-full max-w-lg shadow-2xl relative">
             <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-cyan-400">Initiate Recovery Protocol</h3>
                <button on:click={() => showRestModal = false} class="text-zinc-500 hover:text-white">✕</button>
            </div>
            
            <div class="grid grid-cols-2 gap-4 mb-8">
                {#each ['Gaming', 'Movie/Series', 'Nature/Outside', 'Nap', 'Reading', 'Social'] as activity}
                    <button 
                        on:click={() => restActivity = activity}
                        class="p-4 rounded-lg border transition-all text-center
                        {restActivity === activity 
                            ? 'bg-cyan-900/20 border-cyan-500 text-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.2)]' 
                            : 'bg-zinc-950 border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300'}"
                    >
                        <span class="block text-sm font-bold uppercase tracking-wider">{activity}</span>
                    </button>
                {/each}
            </div>

            <div class="flex justify-end gap-4 pt-4 border-t border-zinc-800">
                <button on:click={() => showRestModal = false} class="px-6 py-2.5 rounded font-medium text-zinc-500 hover:text-white transition-colors">Cancel</button>
                <button 
                    on:click={handleRestStart} 
                    disabled={!restActivity}
                    class="bg-cyan-600 hover:bg-cyan-500 text-white px-8 py-2.5 rounded font-bold transition-colors shadow-lg shadow-cyan-900/20 disabled:opacity-50 disabled:cursor-not-allowed">
                    Start Recovery
                </button>
            </div>
        </div>
    </div>
  {/if}

  {#if showEndModal}
    <div class="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-zinc-900 border border-zinc-800 w-full max-w-3xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div class="p-6 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-start">
                <div>
                    <h3 class="text-xl font-bold text-white">Debrief Protocol</h3>
                    <p class="text-zinc-500 text-sm mt-1">{$sessionStore.active?.context.project_name}</p>
                </div>
                <button on:click={() => showEndModal = false} class="text-zinc-500 hover:text-white px-2">✕</button>
            </div>
            <div class="p-8 overflow-y-auto space-y-8 scrollbar-thin scrollbar-thumb-zinc-700">
                 <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div class="space-y-3">
                        <label class="block text-xs uppercase tracking-wider text-zinc-500 font-bold">Status</label>
                        <select bind:value={endSessionData.completion_status} class="w-full bg-black border border-zinc-700 rounded px-4 py-3 text-white focus:border-emerald-500 outline-none">
                            <option>Completed</option><option>Good progress</option><option>Minor progress</option><option>Blocked</option><option>Abandoned</option>
                        </select>
                    </div>
                    <div class="space-y-3">
                        <label class="block text-xs uppercase tracking-wider text-zinc-500 font-bold">Work Type (Update)</label>
                        <select bind:value={endSessionData.work_type} class="w-full bg-black border border-zinc-700 rounded px-4 py-3 text-white focus:border-emerald-500 outline-none">
                            <option>Deep</option><option>Shallow</option><option>Maintenance</option><option>Unknown</option>
                        </select>
                        <p class="text-xs text-zinc-600 mt-1">Update if initial categorization was wrong</p>
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div class="space-y-3">
                        <label class="block text-xs uppercase tracking-wider text-zinc-500 font-bold">Moves Goal?</label>
                        <div class="flex gap-4 pt-2">
                            <label class="flex items-center gap-2 cursor-pointer group">
                                <input type="radio" bind:group={endSessionData.moves_main_goal} value={true} class="accent-emerald-500 w-4 h-4">
                                <span class="text-white group-hover:text-emerald-400">Yes</span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer group">
                                <input type="radio" bind:group={endSessionData.moves_main_goal} value={false} class="accent-red-500 w-4 h-4">
                                <span class="text-zinc-400 group-hover:text-red-400">No</span>
                            </label>
                        </div>
                    </div>
                </div>
                <div class="space-y-6 border-t border-zinc-800 pt-6">
                    {#each ['Progress', 'Focus', 'Quality'] as metric}
                        {@const field = metric === 'Progress' ? 'progress_rating' : metric === 'Focus' ? 'focus_quality' : 'quality_rating'}
                        {@const color = metric === 'Progress' ? 'emerald' : metric === 'Focus' ? 'blue' : 'violet'}
                        <div>
                            <div class="flex justify-between mb-2">
                                <label class="text-xs font-bold text-zinc-500 uppercase tracking-wider">{metric}</label>
                                <span class="text-{color}-400 font-mono">{endSessionData[field]}/5</span>
                            </div>
                            <div class="flex gap-2">
                                {#each [1, 2, 3, 4, 5] as r}
                                    <label class="flex-1 cursor-pointer">
                                        <input type="radio" bind:group={endSessionData[field]} value={r} class="hidden peer">
                                        <div class="h-10 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-500 peer-checked:bg-{color}-600/20 peer-checked:text-{color}-400 peer-checked:border-{color}-500 hover:bg-zinc-700 transition-all font-mono text-sm">
                                            {r}
                                        </div>
                                    </label>
                                {/each}
                            </div>
                        </div>
                    {/each}
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 border-t border-zinc-800">
                    <div class="space-y-4">
                         <div class="space-y-2"><label class="text-xs font-bold text-zinc-500 uppercase">Energy After</label><input type="number" bind:value={endSessionData.energy_after} class="w-full bg-black border border-zinc-700 rounded px-3 py-2.5 text-white outline-none focus:border-emerald-500"></div>
                         <div class="space-y-2"><label class="text-xs font-bold text-zinc-500 uppercase">Stress After</label><input type="number" bind:value={endSessionData.stress_after} class="w-full bg-black border border-zinc-700 rounded px-3 py-2.5 text-white outline-none focus:border-emerald-500"></div>
                         <div class="space-y-2"><label class="text-xs font-bold text-zinc-500 uppercase">Feel Tag</label><input bind:value={endSessionData.feel_tag} class="w-full bg-black border border-zinc-700 rounded px-3 py-2.5 text-white outline-none focus:border-emerald-500" placeholder="e.g. satisfied"></div>
                    </div>
                    <div class="space-y-2">
                        <label class="text-xs font-bold text-zinc-500 uppercase">Evidence</label>
                        <textarea bind:value={endSessionData.evidence_note} class="w-full h-full min-h-[180px] bg-black border border-zinc-700 rounded px-4 py-3 text-white resize-none outline-none focus:border-emerald-500 font-mono text-sm" placeholder="Paste link or notes..."></textarea>
                    </div>
                </div>
            </div>
            <div class="p-6 border-t border-zinc-800 flex justify-end gap-4 bg-zinc-900">
                 <button on:click={() => showEndModal = false} class="px-6 py-2 rounded font-medium text-zinc-500 hover:text-white transition-colors">Cancel</button>
                 <button on:click={confirmEndSession} class="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-2 rounded font-bold shadow-lg shadow-emerald-900/20 transition-colors">Log Session</button>
            </div>
        </div>
     </div>
  {/if}

  {#if showDetailModal && selectedSession}
    <div class="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-xl w-full max-w-2xl shadow-2xl relative">
            <div class="flex justify-between items-start mb-6 border-b border-zinc-800 pb-4">
                <div>
                    <h3 class="text-xl font-bold text-white tracking-tight">{selectedSession.context.project_name}</h3>
                    <div class="flex gap-2 mt-2">
                        <span class="text-xs font-mono bg-zinc-800 px-2 py-1 rounded text-zinc-400 border border-zinc-700">{selectedSession.context.domain}</span>
                        <span class="text-xs font-mono bg-zinc-800 px-2 py-1 rounded text-zinc-400 border border-zinc-700">{selectedSession.context.work_type}</span>
                    </div>
                </div>
                <button on:click={() => showDetailModal = false} class="text-zinc-500 hover:text-white">✕</button>
            </div>
            <div class="space-y-8">
                <div class="grid grid-cols-2 gap-8">
                    <div class="space-y-2">
                         <h4 class="text-xs uppercase font-bold text-zinc-500 tracking-wider mb-2">Entry State</h4>
                         <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                            <span class="text-xs text-zinc-400">Energy</span>
                            <div class="flex gap-1">
                                {#each Array(10) as _, i}
                                    <div class="w-1 h-3 rounded-full {i < selectedSession.before.energy ? 'bg-emerald-500' : 'bg-zinc-800'}"></div>
                                {/each}
                            </div>
                         </div>
                         <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                            <span class="text-xs text-zinc-400">Stress</span>
                            <div class="flex gap-1">
                                {#each Array(10) as _, i}
                                    <div class="w-1 h-3 rounded-full {i < selectedSession.before.stress ? 'bg-rose-500' : 'bg-zinc-800'}"></div>
                                {/each}
                            </div>
                         </div>
                    </div>
                    <div class="space-y-2">
                         <h4 class="text-xs uppercase font-bold text-zinc-500 tracking-wider mb-2">Exit State</h4>
                         {#if selectedSession.outcome}
                             <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                                <span class="text-xs text-zinc-400">Energy</span>
                                <div class="flex gap-1">
                                    {#each Array(10) as _, i}
                                        <div class="w-1 h-3 rounded-full {i < selectedSession.after.energy ? 'bg-emerald-500' : 'bg-zinc-800'}"></div>
                                    {/each}
                                </div>
                             </div>
                             <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                                <span class="text-xs text-zinc-400">Stress</span>
                                <div class="flex gap-1">
                                    {#each Array(10) as _, i}
                                        <div class="w-1 h-3 rounded-full {i < selectedSession.after.stress ? 'bg-rose-500' : 'bg-zinc-800'}"></div>
                                    {/each}
                                </div>
                             </div>
                         {:else}
                            <div class="h-full flex items-center justify-center text-xs text-zinc-600 italic border border-dashed border-zinc-800 rounded">
                                Session In Progress
                            </div>
                         {/if}
                    </div>
                </div>
                {#if selectedSession.outcome}
                    <div class="bg-zinc-950 p-5 rounded-lg border border-zinc-800 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full bg-{selectedSession.outcome.completion_status === 'Completed' ? 'emerald' : 'amber'}-500"></div>
                        <div class="grid grid-cols-3 gap-4 text-center mb-4">
                            <div><div class="text-zinc-500 text-[10px] uppercase font-bold">Progress</div><div class="text-emerald-400 font-mono text-xl">{selectedSession.outcome.progress_rating}/5</div></div>
                            <div><div class="text-zinc-500 text-[10px] uppercase font-bold">Focus</div><div class="text-blue-400 font-mono text-xl">{selectedSession.outcome.focus_quality}/5</div></div>
                            <div><div class="text-zinc-500 text-[10px] uppercase font-bold">Quality</div><div class="text-violet-400 font-mono text-xl">{selectedSession.outcome.quality_rating}/5</div></div>
                        </div>
                        <div class="text-sm text-zinc-300 font-mono whitespace-pre-wrap bg-black/30 p-3 rounded border border-zinc-800/50">{selectedSession.outcome.evidence_note || "No evidence recorded."}</div>
                        
                        <div class="flex gap-4 mt-4 pt-4 border-t border-zinc-800/50">
                             <div class="text-xs text-zinc-500">Feeling: <span class="text-white font-bold uppercase">{selectedSession.after?.feel_tag}</span></div>
                             <div class="text-xs text-zinc-500">Duration: <span class="text-white font-mono">{selectedSession.duration_minutes}m</span></div>
                        </div>
                    </div>
                {/if}
            </div>
            <div class="mt-8 pt-4 border-t border-zinc-800 flex justify-between items-center">
                <button on:click={() => handleDelete(selectedSession.id)} class="text-red-500 hover:text-red-400 text-xs font-bold uppercase tracking-wider transition-colors">Delete Record</button>
                <button on:click={() => showDetailModal = false} class="bg-white text-black px-6 py-2 rounded font-bold hover:bg-zinc-200 transition-colors">Close</button>
            </div>
        </div>
    </div>
  {/if}

  {#if showManualModal}
    <div class="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-xl w-full max-w-4xl shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-6 border-b border-zinc-800 pb-4">
                <h3 class="text-xl font-bold text-white">Manual Log Entry</h3>
                <button on:click={() => showManualModal = false} class="text-zinc-500 hover:text-white">✕</button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="space-y-6">
                    <div class="grid grid-cols-2 gap-4">
                        <div class="space-y-2"><label class="text-xs uppercase font-bold text-zinc-500">Start Time</label><input type="datetime-local" bind:value={manualSession.start_time} class="w-full bg-black border border-zinc-700 rounded px-3 py-2 text-white"></div>
                        <div class="space-y-2"><label class="text-xs uppercase font-bold text-zinc-500">End Time</label><input type="datetime-local" bind:value={manualSession.end_time} class="w-full bg-black border border-zinc-700 rounded px-3 py-2 text-white"></div>
                    </div>
                    <div class="space-y-2"><label class="text-xs uppercase font-bold text-zinc-500">Domain</label><select bind:value={manualSession.domain} class="w-full bg-black border border-zinc-700 rounded px-3 py-2 text-white"><option>Work</option><option>Personal Project</option><option>College</option><option>Learning</option><option>Admin</option><option>Health</option><option>Relationships</option></select></div>
                    <div class="space-y-2"><label class="text-xs uppercase font-bold text-zinc-500">Project</label><input bind:value={manualSession.project_name} class="w-full bg-black border border-zinc-700 rounded px-3 py-2 text-white"></div>
                    <div class="space-y-2"><label class="text-xs uppercase font-bold text-zinc-500">Activity</label><input bind:value={manualSession.activity_description} class="w-full bg-black border border-zinc-700 rounded px-3 py-2 text-white"></div>
                    <div class="grid grid-cols-3 gap-4 pt-4">
                        <div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Energy (Before)</label><input type="number" bind:value={manualSession.energy_before} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div>
                        <div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Stress (Before)</label><input type="number" bind:value={manualSession.stress_before} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div>
                        <div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Resistance</label><input type="number" bind:value={manualSession.resistance_before} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div>
                    </div>
                </div>
                <div class="space-y-6">
                    <div class="space-y-2"><label class="text-xs uppercase font-bold text-zinc-500">Status</label><select bind:value={manualSession.completion_status} class="w-full bg-black border border-zinc-700 rounded px-3 py-2 text-white"><option>Completed</option><option>Good progress</option><option>Minor progress</option><option>Blocked</option><option>Abandoned</option></select></div>
                    <div class="space-y-2"><label class="block text-xs uppercase tracking-wider text-zinc-500 font-bold">Moves Goal?</label><div class="flex gap-4 pt-2"><label class="flex items-center gap-2 cursor-pointer group"><input type="radio" bind:group={manualSession.moves_main_goal} value={true} class="accent-emerald-500 w-4 h-4"><span class="text-white group-hover:text-emerald-400">Yes</span></label><label class="flex items-center gap-2 cursor-pointer group"><input type="radio" bind:group={manualSession.moves_main_goal} value={false} class="accent-red-500 w-4 h-4"><span class="text-zinc-400 group-hover:text-red-400">No</span></label></div></div>
                    <div class="grid grid-cols-3 gap-4"><div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Progress</label><input type="number" min="1" max="5" bind:value={manualSession.progress_rating} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div><div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Focus</label><input type="number" min="1" max="5" bind:value={manualSession.focus_quality} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div><div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Quality</label><input type="number" min="1" max="5" bind:value={manualSession.quality_rating} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div></div>
                    <div class="grid grid-cols-2 gap-4"><div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Energy (After)</label><input type="number" bind:value={manualSession.energy_after} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div><div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Stress (After)</label><input type="number" bind:value={manualSession.stress_after} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white"></div></div>
                    <div class="space-y-1"><label class="text-[10px] uppercase font-bold text-zinc-500">Feel Tag</label><input bind:value={manualSession.feel_tag} class="w-full bg-black border border-zinc-700 rounded px-2 py-1 text-white" placeholder="e.g. satisfied"></div>
                    <div class="space-y-2"><label class="text-xs uppercase font-bold text-zinc-500">Evidence</label><textarea bind:value={manualSession.evidence_note} class="w-full h-16 bg-black border border-zinc-700 rounded px-3 py-2 text-white resize-none"></textarea></div>
                </div>
            </div>
            <div class="mt-8 pt-4 border-t border-zinc-800 flex justify-end gap-4"><button on:click={() => showManualModal = false} class="px-6 py-2 rounded font-medium text-zinc-500 hover:text-white transition-colors">Cancel</button><button on:click={handleManualSubmit} class="bg-violet-600 hover:bg-violet-500 text-white px-8 py-2 rounded font-bold shadow-lg shadow-violet-900/20 transition-colors">Save Past Session</button></div>
        </div>
    </div>
  {/if}

</main>