import { ClerkProvider } from "@clerk/nextjs";
import type { AppProps } from "next/app";
// react-datepicker's CSS import can trigger PostCSS transforms in dev which
// cause Turbopack to attempt native transforms. Remove the direct import and
// rely on the compiled Tailwind output for now. If you need datepicker styles
// re-added, we can copy them into a static stylesheet.
import "../styles/tailwind-output.css";
import { useEffect } from 'react';

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    // no-op; tailwind will be compiled at build time
  }, []);
  return (
    <ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY} {...pageProps}>
      <Component {...pageProps} />
    </ClerkProvider>
  );
}
