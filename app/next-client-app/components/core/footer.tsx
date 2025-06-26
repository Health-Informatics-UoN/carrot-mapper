import Link from "next/link";
import { ReceiptText, ShieldQuestion } from "lucide-react";

const Footer = () => {
  return (
    <footer className="lg:mt-24 mt-20 mb-5 rounded-lg shadow bg-background">
      <div className="w-full max-w-screen-xl mx-auto p-4 md:py-8">
        <div className="sm:flex sm:items-center sm:justify-between">
          <Link href={"https://www.nottingham.ac.uk/"}>
            <img
              className="dark:hidden w-[200px]"
              src="/logos/UoN-light.png"
              alt="UoN Logo"
            />
            <img
              className="hidden dark:block w-[200px]"
              src="/logos/UoN-dark.png"
              alt="UoN Logo"
            />
          </Link>
          <ul className="flex flex-wrap mt-3 sm:mt-0 items-center mb-6 text-sm font-medium text-muted-foreground sm:mb-0">
            <li>
              <a
                href="https://www.nottingham.ac.uk/utilities/privacy/privacy.aspx"
                className="hover:underline me-4 md:me-6 flex items-center mb-2 sm:mb-0"
              >
                <ShieldQuestion className="mr-2" /> Privacy Policy
              </a>
            </li>
            <li>
              <a
                href="https://www.nottingham.ac.uk/utilities/terms.aspx"
                className="hover:underline me-4 md:me-6 flex items-center"
              >
                <ReceiptText className="mr-2" />
                Terms and Conditions
              </a>
            </li>
          </ul>
        </div>
        <hr className="my-6 border-border sm:mx-auto lg:my-8" />
        <span className="text-pretty block text-sm text-muted-foreground sm:text-center">
          &copy; {new Date().getFullYear()}{" "}
          <a href="https://www.nottingham.ac.uk/" className="hover:underline">
            University of Nottingham
          </a>
          . All Rights Reserved.
        </span>
      </div>
    </footer>
  );
};

export default Footer;
