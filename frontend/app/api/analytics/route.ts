import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const backendDir = path.resolve(process.cwd(), '../backend');
    const cmd = `uv run python src/analytics_data.py`;
    
    return new Promise<Response>((resolve) => {
      exec(cmd, { cwd: backendDir }, (error, stdout, stderr) => {
        if (error) {
          console.error('Error fetching analytics:', stderr);
          resolve(
            NextResponse.json(
              { success: false, message: 'Execution failed', error: stderr },
              { status: 500 }
            )
          );
        } else {
          try {
            // Find the JSON output, ignoring any uv logs
            const lines = stdout.trim().split('\n');
            const resultStr = lines.slice(lines.findIndex(l => l.startsWith('{'))).join('\n');
            const result = JSON.parse(resultStr);
            resolve(NextResponse.json(result));
          } catch (e) {
            resolve(
              NextResponse.json(
                { success: false, message: 'Failed to parse JSON', stdout },
                { status: 500 }
              )
            );
          }
        }
      });
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, message: 'Internal Server Error' },
      { status: 500 }
    );
  }
}
