import { useState } from 'react';
import { Button } from '@/components/ui/button';
import Image from 'next/image';
import { Microphone, WarningCircle, CircleNotch, PhoneOutgoing } from '@phosphor-icons/react';

function WelcomeImage() {
  return (
    <div className="relative mb-8 flex size-32 md:size-40 items-center justify-center">
      <div className="absolute inset-0 rounded-full bg-emerald-500/30 blur-[40px] animate-pulse-slow"></div>
      <Image
        src="/avatar.png"
        alt="Financial Advisor Avatar"
        fill
        className="rounded-full border-2 border-emerald-500/50 shadow-2xl object-cover relative z-10"
      />
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  isCallEnded?: boolean;
  isConnecting?: boolean;
  errorState?: string | null;
  onResetError?: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  isCallEnded,
  isConnecting,
  errorState,
  onResetError,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {

  const [phoneNumber, setPhoneNumber] = useState('');
  const [outboundState, setOutboundState] = useState<'idle' | 'calling' | 'success' | 'failed'>('idle');

  const handleOutboundCall = async () => {
    setOutboundState('calling');
    try {
      const res = await fetch('/api/outbound', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: 'shazilparwez', scheme: 'PMSBY' })
      });
      const data = await res.json();
      if (data.success) {
        setOutboundState('success');
        setTimeout(() => setOutboundState('idle'), 5000);
      } else {
        setOutboundState('failed');
      }
    } catch (e) {
      setOutboundState('failed');
    }
  };

  const handleTryAgain = () => {
    if (onResetError) onResetError();
  };

  if (errorState) {
    return (
      <div ref={ref} className="flex h-full flex-col items-center justify-center text-center px-4">
        <WarningCircle size={64} weight="duotone" className="text-destructive mb-6" />
        <h1 className="text-foreground mt-2 text-2xl font-bold tracking-tight md:text-3xl text-balance">
          Microphone access is blocked
        </h1>
        <p className="text-muted-foreground max-w-prose pt-3 leading-7 font-medium md:text-lg">
          Please allow microphone access in your browser settings and try again.
        </p>
        <Button
          size="lg"
          onClick={handleTryAgain}
          className="mt-8 w-64 rounded-full font-semibold text-sm tracking-wide bg-primary hover:bg-primary/90 text-primary-foreground shadow-xl transition-all"
        >
          Try Again
        </Button>
      </div>
    );
  }

  if (isConnecting) {
    return (
      <div ref={ref} className="flex h-full flex-col items-center justify-center text-center px-4">
        <div className="relative mb-6 flex size-24 md:size-28 items-center justify-center">
          <CircleNotch size={64} weight="bold" className="text-primary animate-spin" />
        </div>
        <h1 className="text-foreground mt-2 text-2xl font-bold tracking-tight md:text-3xl text-balance animate-pulse">
          Connecting to FinSathi...
        </h1>
        <p className="text-muted-foreground max-w-prose pt-3 leading-7 font-medium md:text-lg">
          Please wait while we connect your voice session.
        </p>
        <Button
          size="lg"
          disabled
          className="mt-8 w-64 rounded-full font-semibold text-sm tracking-wide bg-primary/50 text-primary-foreground shadow-xl"
        >
          Connecting...
        </Button>
      </div>
    );
  }

  return (
    <div ref={ref} className="flex h-full flex-col items-center justify-center overflow-y-auto">
      <section className="relative z-10 flex flex-col items-center justify-center text-center px-10 py-12 bg-white/5 border border-white/10 backdrop-blur-2xl shadow-2xl rounded-[3rem] max-w-2xl mx-4 mt-8 mb-24">
        <WelcomeImage />

        <h1 className="text-white mt-2 text-3xl font-bold tracking-tight md:text-5xl text-balance">
          {isCallEnded ? 'Conversation ended' : 'फिन साथी'}
        </h1>
        <p className="text-emerald-100/70 max-w-prose pt-4 leading-7 font-medium md:text-lg">
          {isCallEnded
            ? 'The conversation has ended.'
            : 'आपका AI Financial Services Assistant'}
        </p>
        
        {!isCallEnded && (
          <div className="mt-6 flex items-center gap-2 text-emerald-400/90 bg-emerald-500/10 px-4 py-2 rounded-full border border-emerald-500/20">
            <Microphone size={20} weight="fill" className="animate-pulse" />
            <span className="text-sm font-semibold tracking-wide uppercase">Voice Ready</span>
          </div>
        )}

        <Button
          size="lg"
          onClick={onStartCall}
          className="mt-10 w-64 rounded-full font-bold text-sm tracking-wider uppercase bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_40px_-10px_rgba(16,185,129,0.5)] transition-all hover:scale-105 hover:shadow-[0_0_60px_-15px_rgba(16,185,129,0.7)] border border-emerald-400/30"
        >
          {isCallEnded ? 'Start Again' : 'Start Conversation'}
        </Button>

        {/* Day 6 Outbound Call Trigger */}
        <div className="mt-12 w-full max-w-sm pt-8 border-t border-white/10 flex flex-col items-center">
          <p className="text-white/80 text-sm font-medium mb-4 uppercase tracking-wider">Day 6: Outbound Call (Linphone SIP)</p>
          <Button
            size="sm"
            onClick={handleOutboundCall}
            disabled={outboundState === 'calling'}
            className="mt-2 w-full rounded-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
          >
            <PhoneOutgoing size={18} className="mr-2" />
            {outboundState === 'idle' ? 'Start Financial Reminder Call' : 
             outboundState === 'calling' ? 'Preparing call...' : 
             outboundState === 'success' ? 'Call connected!' : 'Call failed'}
          </Button>
          <p className="text-xs text-white/50 mt-3 text-center">This will initiate an outbound call to <b>shazilparwez</b> via LiveKit SIP trunk.</p>
        </div>

      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center bg-transparent pointer-events-none">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm pointer-events-auto">
          Powered by{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://livekit.io/"
            className="underline text-emerald-400"
          >
            LiveKit
          </a>
          .
        </p>
      </div>
    </div>
  );
};

