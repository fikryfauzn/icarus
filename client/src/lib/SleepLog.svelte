<script>
  import { onMount } from 'svelte';
  import { post } from './api';

  // Default to "Today" (Morning of...)
  let date = new Date().toISOString().split('T')[0];
  
  // Default times: Yesterday 23:00 to Today 07:00
  let yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
  let startStr = `${yesterday.toISOString().split('T')[0]}T23:00`;
  let endStr = `${date}T07:00`;

  let form = {
    sleep_quality: 4,
    awakenings_count: 0,
    energy_morning: 7,
    mood_morning: 7,
    screen_last_hour: false,
    caffeine_after_17: false,
    bedtime_consistent: true
  };

  let saving = false;
  let message = "";

  // Computed Duration
  $: duration = calculateDuration(startStr, endStr);

  function calculateDuration(s, e) {
    if (!s || !e) return 0;
    const diff = new Date(e) - new Date(s);
    return Math.max(0, Math.floor(diff / 1000 / 60)); // in minutes
  }

  function formatDuration(mins) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return `${h}h ${m}m`;
  }

  async function handleSubmit() {
    saving = true;
    message = "";
    try {
        const payload = {
            date: date,
            sleep_start: startStr, 
            sleep_end: endStr,
            ...form
        };
        
        await post('/sleep', payload);
        message = "Sleep log saved successfully.";
        
        // Optional: Reset or redirect
        setTimeout(() => message = "", 3000);
    } catch (e) {
        console.error(e);
        message = "Error: " + e.message;
    } finally {
        saving = false;
    }
  }
</script>

<div class="max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
    
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl">
        <div class="p-8 border-b border-zinc-800 bg-zinc-900/50">
            <h2 class="text-2xl font-bold text-white">Sleep Protocol</h2>
            <p class="text-zinc-500 text-sm mt-1">Log the input parameters for your biological engine.</p>
        </div>

        <div class="p-8 space-y-8">
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-bold">Waking Date</label>
                    <input type="date" bind:value={date} class="w-full bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white focus:border-violet-500 outline-none transition-all" />
                </div>
                 <div class="space-y-2 flex flex-col justify-end pb-3">
                    <div class="text-xs uppercase tracking-wider text-zinc-600 font-bold text-right">Calculated Duration</div>
                    <div class="text-2xl font-mono text-right {duration < 360 ? 'text-red-500' : duration > 540 ? 'text-emerald-500' : 'text-violet-400'}">
                        {formatDuration(duration)}
                    </div>
                </div>
                
                <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-bold">Bed Time</label>
                    <input type="datetime-local" bind:value={startStr} class="w-full bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white focus:border-violet-500 outline-none transition-all font-mono text-sm" />
                </div>
                <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-bold">Wake Time</label>
                    <input type="datetime-local" bind:value={endStr} class="w-full bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white focus:border-violet-500 outline-none transition-all font-mono text-sm" />
                </div>
            </div>

            <div class="border-t border-zinc-800"></div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                
                <div class="space-y-4">
                     <div class="flex justify-between">
                        <label class="text-xs uppercase tracking-wider text-zinc-500 font-bold">Sleep Quality</label>
                        <span class="text-violet-400 font-mono">{form.sleep_quality}/5</span>
                    </div>
                    <input type="range" min="1" max="5" bind:value={form.sleep_quality} class="w-full accent-violet-500 h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer">
                    <div class="flex justify-between text-[10px] text-zinc-600 font-mono px-1">
                        <span>Restless</span><span>Deep</span>
                    </div>
                </div>

                <div class="space-y-4">
                     <div class="flex justify-between">
                        <label class="text-xs uppercase tracking-wider text-zinc-500 font-bold">Awakenings</label>
                        <span class="text-zinc-300 font-mono">{form.awakenings_count}</span>
                    </div>
                    <div class="flex gap-2">
                        <button on:click={() => form.awakenings_count = Math.max(0, form.awakenings_count - 1)} class="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded py-2">-</button>
                        <button on:click={() => form.awakenings_count++} class="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white rounded py-2">+</button>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-bold">Morning Energy (1-10)</label>
                    <input type="number" min="1" max="10" bind:value={form.energy_morning} class="w-full bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white focus:border-emerald-500 outline-none" />
                </div>
                 <div class="space-y-2">
                    <label class="text-xs uppercase tracking-wider text-zinc-500 font-bold">Morning Mood (1-10)</label>
                    <input type="number" min="1" max="10" bind:value={form.mood_morning} class="w-full bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white focus:border-blue-500 outline-none" />
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                
                <label class="flex items-center gap-3 p-4 rounded-lg border border-zinc-800 bg-zinc-900/50 cursor-pointer hover:border-zinc-600 transition-colors">
                    <input type="checkbox" bind:checked={form.screen_last_hour} class="w-5 h-5 rounded border-zinc-600 bg-black text-violet-500 focus:ring-offset-black focus:ring-violet-500">
                    <div>
                        <div class="text-sm font-medium text-zinc-300">Screens</div>
                        <div class="text-[10px] text-zinc-500">Last 1 hour</div>
                    </div>
                </label>

                <label class="flex items-center gap-3 p-4 rounded-lg border border-zinc-800 bg-zinc-900/50 cursor-pointer hover:border-zinc-600 transition-colors">
                    <input type="checkbox" bind:checked={form.caffeine_after_17} class="w-5 h-5 rounded border-zinc-600 bg-black text-violet-500 focus:ring-offset-black focus:ring-violet-500">
                    <div>
                        <div class="text-sm font-medium text-zinc-300">Caffeine</div>
                        <div class="text-[10px] text-zinc-500">After 17:00</div>
                    </div>
                </label>

                <label class="flex items-center gap-3 p-4 rounded-lg border border-zinc-800 bg-zinc-900/50 cursor-pointer hover:border-zinc-600 transition-colors">
                    <input type="checkbox" bind:checked={form.bedtime_consistent} class="w-5 h-5 rounded border-zinc-600 bg-black text-violet-500 focus:ring-offset-black focus:ring-violet-500">
                    <div>
                        <div class="text-sm font-medium text-zinc-300">Routine</div>
                        <div class="text-[10px] text-zinc-500">Consistent time</div>
                    </div>
                </label>

            </div>

            {#if message}
                <div class="p-4 rounded-lg bg-emerald-900/20 text-emerald-400 border border-emerald-900/50 text-center text-sm">
                    {message}
                </div>
            {/if}

            <div class="pt-4 flex justify-end">
                <button 
                    on:click={handleSubmit} 
                    disabled={saving}
                    class="bg-violet-600 hover:bg-violet-500 text-white px-8 py-3 rounded-xl font-bold transition-all shadow-lg shadow-violet-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {saving ? 'Logging...' : 'Log Sleep Record'}
                </button>
            </div>

        </div>
    </div>
</div>