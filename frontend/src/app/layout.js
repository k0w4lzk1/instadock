import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/lib/ThemeProvider"; 
// FIX: Import the wrapper instead of the Navbar component directly
import ThemeWrapper from "@/components/ThemeWrapper"; 

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "InstaDock - Container Service",
  description: "InstaDock: Docker Container Instantiation Platform",
};

export default function RootLayout({ children }) {
  return (
    // The class 'dark' is managed by the ThemeProvider applying it to document.documentElement
    <html lang="en" className="dark"> 
      <body className={inter.className}>
        <ThemeProvider>
          {/* CRITICAL FIX: Render the Navbar via the Client Component wrapper */}
          <ThemeWrapper /> 
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}