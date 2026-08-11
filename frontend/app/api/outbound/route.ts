import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';

export async function POST(req: Request) {
  try {
    const { phone_number, scheme } = await req.json();

    if (!phone_number) {
      return NextResponse.json({ success: false, message: 'Phone number is required.' }, { status: 400 });
    }

    // Path to the backend directory
    const backendDir = path.resolve(process.cwd(), '../backend');

    // Make sure we pass the arguments safely.
    // Replace any unsafe characters. (A basic sanitization for the phone number).
    const safePhone = phone_number.replace(/[^a-zA-Z0-9\+@\.:-]/g, '');
    const safeScheme = scheme ? scheme.replace(/[^a-zA-Z0-9]/g, '') : 'PMSBY';

    // Ensure we trigger the outbound call python script
    const cmd = `uv run python src/outbound_call.py ${safePhone} ${safeScheme}`;
    
    return new Promise((resolve) => {
      exec(cmd, { cwd: backendDir }, (error, stdout, stderr) => {
        console.log('Outbound call execution output:', stdout);
        if (error) {
          console.error('Error executing outbound call:', stderr);
          resolve(
            NextResponse.json({ success: false, message: 'Execution failed', error: stderr }, { status: 500 })
          );
        } else {
          // Output contains JSON from the python script at the very end
          try {
            const lines = stdout.trim().split('\n');
            const resultStr = lines.slice(lines.findIndex(l => l.startsWith('{'))).join('\n');
            const result = JSON.parse(resultStr);
            resolve(NextResponse.json(result));
          } catch (e) {
            resolve(NextResponse.json({ success: true, stdout }));
          }
        }
      });
    });
  } catch (error) {
    return NextResponse.json({ success: false, message: 'Internal Server Error' }, { status: 500 });
  }
}
